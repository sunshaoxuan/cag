from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any


CODE_LANGUAGE_BY_SUFFIX = {
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".h": "c",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".php": "php",
    ".ps1": "powershell",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "bash",
    ".sql": "sql",
    ".ts": "typescript",
    ".tsx": "tsx",
}

_DEFINITION_TYPES = {
    "class_declaration": "class",
    "class_definition": "class",
    "interface_declaration": "interface",
    "struct_item": "struct",
    "struct_specifier": "struct",
    "enum_declaration": "enum",
    "enum_item": "enum",
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    "method_declaration": "method",
    "method_definition": "method",
    "method": "method",
}
_CALL_TYPES = {
    "call",
    "call_expression",
    "function_call",
    "invocation_expression",
    "method_invocation",
}
_IMPORT_TYPES = {
    "import_declaration",
    "import_from_statement",
    "import_statement",
    "include_directive",
    "require",
    "use_declaration",
    "using_directive",
}
_IGNORED_CALL_NAMES = {
    "catch",
    "for",
    "if",
    "return",
    "sizeof",
    "switch",
    "while",
}


@dataclass(frozen=True)
class CodeSymbolFact:
    kind: str
    name: str
    qualified_name: str
    signature: str
    start_line: int
    end_line: int
    references: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    parser: str = "fallback"

    @property
    def content_hash(self) -> str:
        payload = (
            f"{self.kind}\n{self.qualified_name}\n{self.signature}\n"
            f"{self.start_line}\n{self.end_line}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CodeChunkFact:
    text: str
    start_line: int
    end_line: int
    symbol_names: tuple[str, ...] = ()
    symbol_kinds: tuple[str, ...] = ()
    parser: str = "fallback"


@dataclass(frozen=True)
class CodeAnalysis:
    language: str
    parser: str
    symbols: tuple[CodeSymbolFact, ...] = ()
    chunks: tuple[CodeChunkFact, ...] = ()
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


def is_code_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in CODE_LANGUAGE_BY_SUFFIX


def analyze_code(
    path: str,
    text: str,
    *,
    chunk_size: int = 3200,
    overlap: int = 320,
) -> CodeAnalysis:
    language = CODE_LANGUAGE_BY_SUFFIX.get(
        PurePosixPath(path).suffix.lower(),
        "",
    )
    if not language:
        return CodeAnalysis(language="text", parser="none")

    diagnostics: list[str] = []
    symbols: list[CodeSymbolFact] = []
    parser_name = "fallback"
    if language == "python":
        try:
            symbols = _analyze_python(text)
            parser_name = "python-ast"
        except (SyntaxError, ValueError) as exc:
            diagnostics.append(f"python-ast: {exc}")
    if not symbols:
        try:
            tree_symbols = _analyze_tree_sitter(language, text)
            if tree_symbols:
                symbols = tree_symbols
                parser_name = "tree-sitter"
        except Exception as exc:
            diagnostics.append(f"tree-sitter: {type(exc).__name__}: {exc}")
    if not symbols:
        symbols = _analyze_fallback(language, text)
        parser_name = "language-fallback"

    module_name = PurePosixPath(path).with_suffix("").as_posix().replace("/", ".")
    imports = tuple(_extract_imports(language, text))
    module_symbol = CodeSymbolFact(
        kind="module",
        name=PurePosixPath(path).stem,
        qualified_name=module_name,
        signature=path,
        start_line=1,
        end_line=max(1, len(text.splitlines())),
        imports=imports,
        parser=parser_name,
    )
    normalized_symbols = [module_symbol]
    for symbol in symbols:
        qualified_name = symbol.qualified_name
        if "." not in qualified_name:
            qualified_name = f"{module_name}.{qualified_name}"
        normalized_symbols.append(
            CodeSymbolFact(
                kind=symbol.kind,
                name=symbol.name,
                qualified_name=qualified_name,
                signature=symbol.signature,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                references=symbol.references,
                imports=symbol.imports,
                parser=parser_name,
            )
        )
    unique_symbols: list[CodeSymbolFact] = []
    seen_identities: set[tuple[str, str, int]] = set()
    for symbol in normalized_symbols:
        identity = (symbol.kind, symbol.qualified_name, symbol.start_line)
        if identity in seen_identities:
            continue
        seen_identities.add(identity)
        unique_symbols.append(symbol)
    chunks = _structure_chunks(
        text,
        unique_symbols[1:],
        parser=parser_name,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    return CodeAnalysis(
        language=language,
        parser=parser_name,
        symbols=tuple(unique_symbols),
        chunks=tuple(chunks),
        diagnostics=tuple(diagnostics),
    )


def _analyze_python(text: str) -> list[CodeSymbolFact]:
    tree = ast.parse(text)
    lines = text.splitlines()
    result: list[CodeSymbolFact] = []

    def walk(body: list[ast.stmt], parents: tuple[str, ...] = ()) -> None:
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = (
                    "class"
                    if isinstance(node, ast.ClassDef)
                    else ("method" if parents else "function")
                )
                end_line = getattr(node, "end_lineno", node.lineno)
                signature = lines[node.lineno - 1].strip() if lines else node.name
                references = tuple(
                    sorted(
                        {
                            _python_call_name(child.func)
                            for child in ast.walk(node)
                            if isinstance(child, ast.Call)
                            and _python_call_name(child.func)
                        }
                    )
                )
                result.append(
                    CodeSymbolFact(
                        kind=kind,
                        name=node.name,
                        qualified_name=".".join((*parents, node.name)),
                        signature=signature[:1000],
                        start_line=node.lineno,
                        end_line=end_line,
                        references=references,
                        parser="python-ast",
                    )
                )
                walk(node.body, (*parents, node.name))

    walk(tree.body)
    return result


def _python_call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _python_call_name(node.value)
        return f"{base}.{node.attr}".strip(".")
    return ""


def _analyze_tree_sitter(language: str, text: str) -> list[CodeSymbolFact]:
    from tree_sitter_language_pack import get_parser

    parser = get_parser(language)
    source = text.encode("utf-8")
    tree = parser.parse(source)
    result: list[CodeSymbolFact] = []

    def node_text(node: Any) -> str:
        return source[node.start_byte : node.end_byte].decode(
            "utf-8",
            errors="replace",
        )

    def name_for(node: Any) -> str:
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return node_text(name_node).strip()
        for child in node.named_children:
            if child.type in {
                "identifier",
                "name",
                "property_identifier",
                "type_identifier",
            }:
                return node_text(child).strip()
        return ""

    def visit(node: Any, parents: tuple[str, ...] = ()) -> None:
        kind = _DEFINITION_TYPES.get(node.type)
        active_parents = parents
        if kind:
            name = name_for(node)
            if name:
                references: set[str] = set()
                imports: set[str] = set()
                stack = list(node.named_children)
                while stack:
                    child = stack.pop()
                    if child.type in _CALL_TYPES:
                        target = child.child_by_field_name("function")
                        if target is None:
                            target = child.child_by_field_name("name")
                        if target is not None:
                            call_name = node_text(target).strip()
                            if call_name and call_name not in _IGNORED_CALL_NAMES:
                                references.add(call_name)
                    if child.type in _IMPORT_TYPES:
                        imports.add(node_text(child).strip())
                    stack.extend(child.named_children)
                first_line = node_text(node).splitlines()[0].strip()
                result.append(
                    CodeSymbolFact(
                        kind=kind,
                        name=name,
                        qualified_name=".".join((*parents, name)),
                        signature=first_line[:1000],
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        references=tuple(sorted(references)),
                        imports=tuple(sorted(imports)),
                        parser="tree-sitter",
                    )
                )
                active_parents = (*parents, name)
        for child in node.named_children:
            visit(child, active_parents)

    visit(tree.root_node)
    return result


def _analyze_fallback(language: str, text: str) -> list[CodeSymbolFact]:
    lines = text.splitlines()
    definitions: list[tuple[int, str, str, str]] = []
    patterns = [
        (
            "class",
            re.compile(
                r"^\s*(?:export\s+|public\s+|private\s+|protected\s+|"
                r"abstract\s+|final\s+)*(?:class|interface|struct|enum)\s+"
                r"([A-Za-z_$][\w$]*)"
            ),
        ),
        (
            "function",
            re.compile(
                r"^\s*(?:export\s+|public\s+|private\s+|protected\s+|"
                r"static\s+|async\s+|final\s+|override\s+)*"
                r"(?:function\s+)?(?:[\w<>\[\],.?]+\s+)?"
                r"([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?:\{|=>|$)"
            ),
        ),
        (
            "function",
            re.compile(
                r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("
            ),
        ),
        (
            "function",
            re.compile(
                r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("
            ),
        ),
        (
            "function",
            re.compile(
                r"^\s*fn\s+([A-Za-z_]\w*)\s*(?:<[^>]+>)?\s*\("
            ),
        ),
    ]
    for index, line in enumerate(lines, start=1):
        for kind, pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            name = match.group(1)
            if name in _IGNORED_CALL_NAMES:
                continue
            definitions.append((index, kind, name, line.strip()[:1000]))
            break
    result: list[CodeSymbolFact] = []
    for position, (start, kind, name, signature) in enumerate(definitions):
        end = (
            definitions[position + 1][0] - 1
            if position + 1 < len(definitions)
            else max(start, len(lines))
        )
        body = "\n".join(lines[start - 1 : end])
        references = tuple(sorted(_extract_calls(body)))
        result.append(
            CodeSymbolFact(
                kind=kind,
                name=name,
                qualified_name=name,
                signature=signature,
                start_line=start,
                end_line=end,
                references=references,
                parser="language-fallback",
            )
        )
    return result


def _extract_calls(text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(",
            text,
        )
        if match.group(1).split(".")[-1] not in _IGNORED_CALL_NAMES
    }


def _extract_imports(language: str, text: str) -> list[str]:
    patterns = [
        r"(?m)^\s*import\s+(?:.+?\s+from\s+)?[\"']?([^\"';\s]+)",
        r"(?m)^\s*from\s+([.\w]+)\s+import\s+",
        r"(?m)^\s*(?:using|use)\s+([^;]+)",
        r"(?m)^\s*#\s*include\s*[<\"]([^>\"]+)",
        r"(?m)^\s*require(?:_once)?\s*\(?[\"']([^\"']+)",
    ]
    imports: set[str] = set()
    for pattern in patterns:
        imports.update(
            match.group(1).strip()
            for match in re.finditer(pattern, text)
            if match.group(1).strip()
        )
    return sorted(imports)


def _structure_chunks(
    text: str,
    symbols: list[CodeSymbolFact],
    *,
    parser: str,
    chunk_size: int,
    overlap: int,
) -> list[CodeChunkFact]:
    lines = text.splitlines()
    chunks: list[CodeChunkFact] = []
    covered: set[int] = set()
    for symbol in sorted(symbols, key=lambda item: (item.start_line, item.end_line)):
        start = max(1, symbol.start_line)
        end = min(len(lines), max(start, symbol.end_line))
        nested_starts = [
            candidate.start_line
            for candidate in symbols
            if candidate.start_line > start and candidate.end_line <= end
        ]
        if nested_starts:
            end = max(start, min(nested_starts) - 1)
        segment = "\n".join(lines[start - 1 : end]).strip()
        if not segment:
            continue
        covered.update(range(start, end + 1))
        for part, part_start, part_end in _split_with_lines(
            segment,
            start_line=start,
            size=chunk_size,
            overlap=overlap,
        ):
            chunks.append(
                CodeChunkFact(
                    text=part,
                    start_line=part_start,
                    end_line=min(end, part_end),
                    symbol_names=(symbol.name,),
                    symbol_kinds=(symbol.kind,),
                    parser=parser,
                )
            )
    remaining_ranges = _contiguous_ranges(
        line for line in range(1, len(lines) + 1) if line not in covered
    )
    for start, end in remaining_ranges:
        segment = "\n".join(lines[start - 1 : end]).strip()
        if not segment:
            continue
        for part, part_start, part_end in _split_with_lines(
            segment,
            start_line=start,
            size=chunk_size,
            overlap=overlap,
        ):
            chunks.append(
                CodeChunkFact(
                    text=part,
                    start_line=part_start,
                    end_line=min(end, part_end),
                    parser=parser,
                )
            )
    return sorted(chunks, key=lambda item: (item.start_line, item.end_line))


def _split_with_lines(
    text: str,
    *,
    start_line: int,
    size: int,
    overlap: int,
) -> list[tuple[str, int, int]]:
    if len(text) <= size:
        return [(text, start_line, start_line + text.count("\n"))]
    result: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        part = text[start:end].strip()
        if part:
            line_offset = text[:start].count("\n")
            result.append(
                (
                    part,
                    start_line + line_offset,
                    start_line + line_offset + part.count("\n"),
                )
            )
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return result


def _contiguous_ranges(values: Any) -> list[tuple[int, int]]:
    sorted_values = sorted(values)
    if not sorted_values:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = sorted_values[0]
    for value in sorted_values[1:]:
        if value != previous + 1:
            ranges.append((start, previous))
            start = value
        previous = value
    ranges.append((start, previous))
    return ranges


def japanese_search_terms(text: str) -> set[str]:
    normalized = text.casefold()
    terms = {
        item
        for item in re.findall(
            r"[a-z_][a-z0-9_.:/-]*|[0-9]+|"
            r"[\u3040-\u30ff\u3400-\u9fff]+",
            normalized,
        )
        if len(item) > 1
    }
    for run in re.findall(r"[\u3040-\u30ff\u3400-\u9fff]+", normalized):
        for width in (2, 3):
            terms.update(
                run[index : index + width]
                for index in range(0, max(0, len(run) - width + 1))
            )
    return terms
