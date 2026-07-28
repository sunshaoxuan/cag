"""顧客情報を検索する構造化コード知識の検証用サービス。"""


def normalize_customer_name(name: str) -> str:
    """顧客名の前後空白を正規化する。"""
    return name.strip()


class CustomerKnowledgeService:
    """顧客別の企業知識を検索する。"""

    def search_customer(self, name: str) -> str:
        """正規化した顧客名を検索条件として返す。"""
        return normalize_customer_name(name)
