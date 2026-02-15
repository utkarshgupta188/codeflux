"""
Documentation Generation Service - AI-powered code documentation.
"""

import os
import logging
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.graph import Symbol, GraphFile
from app.models.version import RepoVersion
from app.services.scanner import ScannerService
from app.services.router import RoutingService
from app.models.api import ChatRequest

logger = logging.getLogger("docs_service")


class GenerateDocsResponse:
    def __init__(
        self,
        documentation: str,
        format: str,
        generated_for: str,
        included_files: list[str],
        truncated: bool,
        stats: dict,
    ):
        self.documentation = documentation
        self.format = format
        self.generated_for = generated_for
        self.included_files = included_files
        self.truncated = truncated
        self.stats = stats


class DocsService:
    SUPPORTED_EXTENSIONS = (
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".cpp",
        ".cc",
        ".cxx",
        ".c",
        ".h",
        ".hpp",
    )
    IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "dist",
        "build",
    }

    MAX_CHARS_PER_FILE = 10000
    DEFAULT_MAX_FILES = {
        "file": 1,
        "folder": 10,
        "repo": 20,
    }
    DEFAULT_MAX_CHARS = 50000

    @staticmethod
    def _resolve_path(root_path: str, path: str) -> Tuple[str, str]:
        normalized = path.replace('\\', '/').strip()
        if normalized in ('', '.', '/', '\\'):
            raise ValueError("Path is required")

        if os.path.isabs(normalized):
            abs_path = normalized
        else:
            abs_path = os.path.join(root_path, normalized.replace('/', os.sep))

        abs_path = os.path.abspath(abs_path)
        root_abs = os.path.abspath(root_path)
        if not abs_path.startswith(root_abs):
            raise ValueError("Path must be within the repository")

        rel_path = os.path.relpath(abs_path, root_abs).replace('\\', '/')
        return abs_path, rel_path

    @staticmethod
    def _collect_files(root_path: str, base_path: str, max_files: int) -> Tuple[List[Tuple[str, str]], int, bool]:
        files: List[Tuple[str, str]] = []

        for root, dirs, filenames in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in DocsService.IGNORE_DIRS]

            for filename in filenames:
                if not filename.endswith(DocsService.SUPPORTED_EXTENSIONS):
                    continue

                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, root_path).replace('\\', '/')
                files.append((file_path, rel_path))

        files.sort(key=lambda item: item[1])
        scanned_count = len(files)
        truncated = False

        if max_files and len(files) > max_files:
            files = files[:max_files]
            truncated = True

        return files, scanned_count, truncated

    @staticmethod
    async def generate(
        scan_id: str,
        scope: str,
        path: Optional[str],
        symbol: Optional[str],
        format: str,
        max_files: Optional[int],
        max_chars: Optional[int],
        db: AsyncSession,
    ) -> GenerateDocsResponse:
        """
        Generate documentation for a file, folder, or repository using AI.
        """
        if scan_id not in ScannerService.SCANS:
            raise ValueError("Scan not found")

        scan = ScannerService.SCANS[scan_id]
        if not scan.rootPath:
            raise ValueError("Repository path not available")

        root_path = scan.rootPath
        scope = (scope or "file").lower()
        if scope not in ("file", "folder", "repo"):
            raise ValueError("Invalid scope. Use 'file', 'folder', or 'repo'.")

        if scope != "file" and symbol:
            raise ValueError("Symbol is only supported for file scope")

        default_max_files = DocsService.DEFAULT_MAX_FILES[scope]
        resolved_max_files = min(max_files or default_max_files, default_max_files)
        resolved_max_chars = min(max_chars or DocsService.DEFAULT_MAX_CHARS, DocsService.DEFAULT_MAX_CHARS)

        included_files: list[str] = []
        truncated = False
        stats = {
            "files_scanned": 0,
            "files_included": 0,
            "total_chars": 0,
            "max_files": resolved_max_files,
            "max_chars": resolved_max_chars,
        }

        if scope == "file":
            if not path:
                raise ValueError("File path is required")

            file_path, rel_path = DocsService._resolve_path(root_path, path)

            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {path}")
            if os.path.isdir(file_path):
                raise ValueError(f"Expected a file, got directory: {path}")

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code_content = f.read()
            except Exception as e:
                raise ValueError(f"Failed to read file: {e}")

            symbol_code = None
            if symbol:
                version_result = await db.execute(
                    select(RepoVersion).where(RepoVersion.scan_id == scan_id)
                )
                version = version_result.scalar_one_or_none()

                if version:
                    files_result = await db.execute(
                        select(GraphFile).where(
                            GraphFile.version_id == version.id,
                            GraphFile.path == rel_path
                        )
                    )
                    file_obj = files_result.scalar_one_or_none()

                    if file_obj:
                        symbols_result = await db.execute(
                            select(Symbol).where(
                                Symbol.file_id == file_obj.id,
                                Symbol.name == symbol
                            )
                        )
                        symbol_obj = symbols_result.scalar_one_or_none()

                        if symbol_obj:
                            lines = code_content.splitlines()
                            start = max(0, symbol_obj.start_line - 1)
                            end = min(len(lines), symbol_obj.end_line)
                            symbol_code = '\n'.join(lines[start:end])

            code_to_document = symbol_code if symbol_code else code_content
            target_name = f"{rel_path}::{symbol}" if symbol else rel_path

            if len(code_to_document) > DocsService.MAX_CHARS_PER_FILE:
                code_to_document = code_to_document[:DocsService.MAX_CHARS_PER_FILE] + "\n... (truncated)"
                truncated = True

            included_files = [rel_path]
            stats["files_scanned"] = 1
            stats["files_included"] = 1
            stats["total_chars"] = len(code_to_document)

        else:
            if scope == "repo":
                base_path = os.path.abspath(root_path)
                target_name = "repo"
            else:
                if not path:
                    raise ValueError("Folder path is required")
                base_path, rel_path = DocsService._resolve_path(root_path, path)
                if not os.path.exists(base_path):
                    raise ValueError(f"Folder not found: {path}")
                if not os.path.isdir(base_path):
                    raise ValueError(f"Expected a folder, got file: {path}")
                target_name = f"folder:{rel_path}"

            files, scanned_count, files_truncated = DocsService._collect_files(
                root_path=root_path,
                base_path=base_path,
                max_files=resolved_max_files,
            )

            if not files:
                raise ValueError("No supported files found for documentation")

            combined_parts: list[str] = []
            total_chars = 0
            truncated = truncated or files_truncated

            for file_path, rel_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Failed to read file {file_path}: {e}")
                    continue

                if len(content) > DocsService.MAX_CHARS_PER_FILE:
                    content = content[:DocsService.MAX_CHARS_PER_FILE] + "\n... (truncated)"
                    truncated = True

                header = f"## File: {rel_path}\n```\n"
                footer = "\n```\n"

                remaining_chars = resolved_max_chars - total_chars - len(header) - len(footer)
                if remaining_chars <= 0:
                    truncated = True
                    break

                if len(content) > remaining_chars:
                    content = content[:remaining_chars] + "\n... (truncated)"
                    truncated = True

                section = f"{header}{content}{footer}"
                combined_parts.append(section)
                total_chars += len(section)
                included_files.append(rel_path)

                if total_chars >= resolved_max_chars:
                    truncated = True
                    break

            code_to_document = "\n".join(combined_parts).strip()
            stats["files_scanned"] = scanned_count
            stats["files_included"] = len(included_files)
            stats["total_chars"] = len(code_to_document)

        if format == "markdown":
            if scope == "file":
                prompt = f"""Generate comprehensive Markdown documentation for the following code from {target_name}.

Include:
1. Overview/Purpose
2. Parameters/Arguments (if applicable)
3. Return values (if applicable)
4. Usage examples
5. Important notes or caveats

Code:
```
{code_to_document}
```

Generate clear, professional documentation in Markdown format."""
            else:
                prompt = f"""Generate comprehensive Markdown documentation for the following {target_name} code.

Include:
1. Overview/Purpose
2. Key components/modules
3. Important interfaces or public APIs
4. Usage examples
5. Important notes or caveats

Code:
{code_to_document}

Generate clear, professional documentation in Markdown format."""

        elif format == "docstring":
            if scope == "file":
                prompt = f"""Generate a docstring for the following code from {target_name}.

Follow best practices for the language (Python docstring, JSDoc, Javadoc, etc.).

Code:
```
{code_to_document}
```

Generate only the docstring, properly formatted for the language."""
            else:
                prompt = f"""Generate docstring-style documentation for the following {target_name} code.

Summarize key modules and describe their responsibilities. Keep the output concise and structured.

Code:
{code_to_document}

Generate only the documentation."""
        else:
            if scope == "file":
                prompt = f"""Generate HTML documentation for the following code from {target_name}.

Include proper HTML structure with sections for overview, parameters, returns, and examples.

Code:
```
{code_to_document}
```

Generate clean, styled HTML documentation."""
            else:
                prompt = f"""Generate HTML documentation for the following {target_name} code.

Include proper HTML structure with sections for overview, key components, and examples.

Code:
{code_to_document}

Generate clean, styled HTML documentation."""

        router = RoutingService()
        chat_request = ChatRequest(
            prompt=prompt,
            system_prompt="You are a technical documentation expert. Generate clear, accurate, and comprehensive documentation.",
            task_type="documentation",
        )

        try:
            result = await router.route_request(chat_request)
            documentation = result["response"]
        except Exception as e:
            logger.error(f"AI documentation generation failed: {e}")
            raise ValueError(f"Failed to generate documentation: {e}")

        return GenerateDocsResponse(
            documentation=documentation,
            format=format,
            generated_for=target_name,
            included_files=included_files,
            truncated=truncated,
            stats=stats,
        )
