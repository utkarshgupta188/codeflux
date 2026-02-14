"""
AST Visitor for structural code analysis.

Extracts modules, classes, functions, methods, imports, and call sites
from Python source files using the built-in `ast` module.
"""

import ast
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("graph.ast_visitor")


# ─── Data structures returned by the visitor ────────────

@dataclass
class SymbolInfo:
    name: str
    qualified_name: str       # e.g. "MyClass.my_method"
    type: str                 # module | class | function | method | import
    start_line: int
    end_line: int


@dataclass
class CallInfo:
    caller_qualified_name: str   # qualified name of the enclosing scope
    callee_name: str             # raw name as written in source
    line: int


@dataclass
class ImportInfo:
    module: str                  # "os.path" or "app.services.scanner"
    names: List[str]             # ["join", "exists"] or ["*"]
    line: int


@dataclass
class FileAnalysis:
    """Result of analyzing a single .py file."""
    relative_path: str
    module_name: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)


# ─── Visitor ────────────────────────────────────────────

class StructuralVisitor(ast.NodeVisitor):
    """
    Walks an AST and collects structural information:
    symbols (classes, functions, methods), imports, and call sites.
    """

    def __init__(self) -> None:
        self.symbols: List[SymbolInfo] = []
        self.calls: List[CallInfo] = []
        self.imports: List[ImportInfo] = []
        self._scope_stack: List[str] = []   # tracks nesting for qualified names

    @property
    def _current_scope(self) -> Optional[str]:
        return self._scope_stack[-1] if self._scope_stack else None

    def _qualified(self, name: str) -> str:
        if self._scope_stack:
            return f"{'.'.join(self._scope_stack)}.{name}"
        return name

    # ── Classes ──────────────────────────────────────

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qname = self._qualified(node.name)
        self.symbols.append(SymbolInfo(
            name=node.name,
            qualified_name=qname,
            type="class",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
        ))
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    # ── Functions / Methods ──────────────────────────

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_method = len(self._scope_stack) > 0
        qname = self._qualified(node.name)
        self.symbols.append(SymbolInfo(
            name=node.name,
            qualified_name=qname,
            type="method" if is_method else "function",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
        ))
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node)

    # ── Imports ──────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ImportInfo(
                module=alias.name,
                names=[],  # bare import — no sub-names
                line=node.lineno,
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        names = [alias.name for alias in node.names] if node.names else ["*"]
        self.imports.append(ImportInfo(
            module=module,
            names=names,
            line=node.lineno,
        ))

    # ── Calls ────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        callee = self._resolve_call_name(node.func)
        if callee:
            self.calls.append(CallInfo(
                caller_qualified_name=".".join(self._scope_stack) if self._scope_stack else "<module>",
                callee_name=callee,
                line=node.lineno,
            ))
        self.generic_visit(node)

    @staticmethod
    def _resolve_call_name(node: ast.expr) -> Optional[str]:
        """Best-effort call target resolution from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))
        return None


# ─── Public API ─────────────────────────────────────────

def parse_file(file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
    """
    Parse a single Python file and return structural analysis.
    Returns None if the file cannot be parsed.
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError) as e:
        logger.warning(f"Cannot read {file_path}: {e}")
        return None

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return None

    # Compute relative path and module name
    try:
        rel = file_path.relative_to(repo_root)
    except ValueError:
        rel = file_path

    rel_posix = rel.as_posix()
    module_name = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")

    visitor = StructuralVisitor()
    visitor.visit(tree)

    # Add a module-level symbol for the file itself
    symbols = [SymbolInfo(
        name=module_name,
        qualified_name=module_name,
        type="module",
        start_line=1,
        end_line=len(source.splitlines()),
    )]

    # Add import symbols
    for imp in visitor.imports:
        if not imp.names:
            # Bare import: `import os`
            symbols.append(SymbolInfo(
                name=imp.module,
                qualified_name=f"{module_name}::{imp.module}",
                type="import",
                start_line=imp.line,
                end_line=imp.line,
            ))
        else:
            for name in imp.names:
                label = f"{imp.module}.{name}" if imp.module else name
                symbols.append(SymbolInfo(
                    name=label,
                    qualified_name=f"{module_name}::{label}",
                    type="import",
                    start_line=imp.line,
                    end_line=imp.line,
                ))

    symbols.extend(visitor.symbols)

    return FileAnalysis(
        relative_path=rel_posix,
        module_name=module_name,
        symbols=symbols,
        calls=visitor.calls,
        imports=visitor.imports,
    )
