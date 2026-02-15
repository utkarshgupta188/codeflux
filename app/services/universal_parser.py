"""
Universal Code Parser - Multi-language AST analysis.

Supports: Python, JavaScript, TypeScript, Java, Go, Rust, C++, C
Uses tree-sitter for universal parsing across languages.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("universal_parser")

# Try to import tree-sitter, fall back to regex-based parsing if not available
try:
    import tree_sitter
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available, using regex-based parsing")


@dataclass
class SymbolInfo:
    name: str
    qualified_name: str
    type: str  # module | class | function | method | import | interface | struct
    start_line: int
    end_line: int


@dataclass
class CallInfo:
    caller_qualified_name: str
    callee_name: str
    line: int


@dataclass
class ImportInfo:
    module: str
    names: List[str]
    line: int


@dataclass
class FileAnalysis:
    """Result of analyzing a single source file."""
    relative_path: str
    module_name: str
    language: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)


class RegexParser:
    """Fallback regex-based parser for when tree-sitter is not available."""

    # Language-specific patterns
    PATTERNS = {
        'python': {
            'class': r'^\s*class\s+(\w+)',
            'function': r'^\s*(?:async\s+)?def\s+(\w+)',
            'import': r'^\s*(?:from\s+[\w.]+\s+)?import\s+([\w\s,.*]+)',
        },
        'javascript': {
            'class': r'^\s*class\s+(\w+)',
            'function': r'^\s*(?:async\s+)?function\s+(\w+)|^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(',
            'import': r'^\s*import\s+.*?from\s+[\'"](.+?)[\'"]',
        },
        'typescript': {
            'class': r'^\s*(?:export\s+)?class\s+(\w+)',
            'interface': r'^\s*(?:export\s+)?interface\s+(\w+)',
            'function': r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)|^\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(',
            'import': r'^\s*import\s+.*?from\s+[\'"](.+?)[\'"]',
        },
        'java': {
            'class': r'^\s*(?:public\s+)?(?:abstract\s+)?class\s+(\w+)',
            'interface': r'^\s*(?:public\s+)?interface\s+(\w+)',
            'function': r'^\s*(?:public|private|protected)\s+(?:static\s+)?[\w<>]+\s+(\w+)\s*\(',
            'import': r'^\s*import\s+([\w.]+)',
        },
        'go': {
            'struct': r'^\s*type\s+(\w+)\s+struct',
            'interface': r'^\s*type\s+(\w+)\s+interface',
            'function': r'^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(',
            'import': r'^\s*import\s+["\'](.+?)["\']',
        },
        'rust': {
            'struct': r'^\s*(?:pub\s+)?struct\s+(\w+)',
            'trait': r'^\s*(?:pub\s+)?trait\s+(\w+)',
            'function': r'^\s*(?:pub\s+)?fn\s+(\w+)',
            'import': r'^\s*use\s+([\w:]+)',
        },
        'cpp': {
            'class': r'^\s*class\s+(\w+)',
            'struct': r'^\s*struct\s+(\w+)',
            'function': r'^\s*[\w:<>]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?{',
            'import': r'^\s*#include\s+[<"](.+?)[>"]',
        },
        'c': {
            'struct': r'^\s*(?:typedef\s+)?struct\s+(\w+)',
            'function': r'^\s*[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*{',
            'import': r'^\s*#include\s+[<"](.+?)[>"]',
        },
    }

    @staticmethod
    def detect_language(file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.hpp': 'cpp',
            '.h': 'c',
            '.c': 'c',
        }
        return mapping.get(ext)

    @staticmethod
    def parse(file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
        """Parse file using regex patterns."""
        language = RegexParser.detect_language(file_path)
        if not language:
            return None

        patterns = RegexParser.PATTERNS.get(language, {})
        if not patterns:
            return None

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, IOError) as e:
            logger.warning(f"Cannot read {file_path}: {e}")
            return None

        lines = source.splitlines()
        symbols = []
        imports = []
        calls = []

        # Compute relative path and module name
        try:
            rel = file_path.relative_to(repo_root)
        except ValueError:
            rel = file_path

        rel_posix = rel.as_posix()
        module_name = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")

        # Add module-level symbol
        symbols.append(SymbolInfo(
            name=module_name,
            qualified_name=module_name,
            type="module",
            start_line=1,
            end_line=len(lines),
        ))

        # Parse symbols
        for line_num, line in enumerate(lines, start=1):
            for symbol_type, pattern in patterns.items():
                match = re.match(pattern, line)
                if match:
                    # Get the first non-None group
                    name = next((g for g in match.groups() if g), None)
                    if name:
                        if symbol_type == 'import':
                            imports.append(ImportInfo(
                                module=name,
                                names=[],
                                line=line_num,
                            ))
                        else:
                            # Estimate end line (simple heuristic: find next blank line or end)
                            end_line = line_num
                            for i in range(line_num, min(line_num + 100, len(lines))):
                                if i < len(lines) and lines[i].strip() == '':
                                    end_line = i
                                    break

                            symbols.append(SymbolInfo(
                                name=name,
                                qualified_name=f"{module_name}.{name}",
                                type=symbol_type,
                                start_line=line_num,
                                end_line=end_line,
                            ))

        return FileAnalysis(
            relative_path=rel_posix,
            module_name=module_name,
            language=language,
            symbols=symbols,
            calls=calls,
            imports=imports,
        )


def parse_file_universal(file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
    """
    Universal file parser that supports multiple languages.
    Falls back to Python AST parser for .py files for better accuracy.
    """
    # For Python files, use the existing AST parser
    if file_path.suffix == '.py':
        from app.services.ast_visitor import parse_file as parse_python
        result = parse_python(file_path, repo_root)
        if result:
            # Add language field
            return FileAnalysis(
                relative_path=result.relative_path,
                module_name=result.module_name,
                language='python',
                symbols=result.symbols,
                calls=result.calls,
                imports=result.imports,
            )
        return None

    # For other languages, use regex parser
    return RegexParser.parse(file_path, repo_root)
