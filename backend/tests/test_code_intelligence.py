from pathlib import Path

from app.knowledge.code_intelligence import (
    analyze_code,
    is_code_path,
    japanese_search_terms,
)
from app.knowledge.extractors import (
    detect_text_encoding,
    extract_text_with_metadata,
)


def test_cp932_and_utf_text_detection(tmp_path: Path) -> None:
    japanese = "顧客情報を検索するサービス"
    cp932_path = tmp_path / "design.txt"
    cp932_path.write_bytes(japanese.encode("cp932"))

    extracted = extract_text_with_metadata(cp932_path)

    assert extracted.text == japanese
    assert extracted.encoding == "cp932"
    assert detect_text_encoding(b"\xef\xbb\xbfhello") == "utf-8-sig"
    assert detect_text_encoding(b"\xff\xfeh\x00i\x00") == "utf-16-le"
    assert detect_text_encoding(b"\xfe\xff\x00h\x00i") == "utf-16-be"
    assert detect_text_encoding("日本語".encode("utf-8")) == "utf-8"


def test_python_analysis_preserves_symbols_calls_and_boundaries() -> None:
    source = """\
from app.store import Repository

def helper(value: str) -> str:
    return value.strip()

class CustomerService:
    def search_customer(self, name: str) -> str:
        return helper(name)
"""

    analysis = analyze_code("src/customer_service.py", source, chunk_size=400)

    assert analysis.language == "python"
    assert analysis.parser == "python-ast"
    symbols = {item.name: item for item in analysis.symbols}
    assert {"customer_service", "helper", "CustomerService", "search_customer"} <= set(
        symbols
    )
    assert "helper" in symbols["search_customer"].references
    assert "app.store" in symbols["customer_service"].imports
    search_chunk = next(
        item for item in analysis.chunks if "search_customer" in item.symbol_names
    )
    assert "def search_customer" in search_chunk.text
    assert search_chunk.start_line == symbols["search_customer"].start_line
    assert sum("def search_customer" in item.text for item in analysis.chunks) == 1


def test_language_fallback_and_japanese_search_terms() -> None:
    source = """\
import { audit } from "./audit";
export class 顧客Service {
  searchCustomer(name: string) {
    return audit(name);
  }
}
"""

    analysis = analyze_code("src/customer.ts", source)

    assert is_code_path("src/customer.ts") is True
    assert is_code_path("docs/customer.md") is False
    assert analysis.language == "typescript"
    assert analysis.parser in {"tree-sitter", "language-fallback"}
    assert any(item.name == "searchCustomer" for item in analysis.symbols)
    terms = japanese_search_terms("顧客情報 searchCustomer")
    assert {"顧客", "情報", "searchcustomer"} <= terms
