import re
import unicodedata


HISTORICAL_DIRECTORY_PREFIXES = ("旧_", "旧-")
HISTORICAL_DIRECTORY_NAMES = {
    "old",
    "旧",
    "back",
    "backup",
    "bak",
    "バックアップ",
}


def is_historical_path(canonical_path: str) -> bool:
    if "#history/" in canonical_path.casefold():
        return True
    for value in canonical_path.replace("\\", "/").split("/")[:-1]:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        segment = re.sub(r"\s+", "", normalized)
        if segment in HISTORICAL_DIRECTORY_NAMES or segment.startswith(
            HISTORICAL_DIRECTORY_PREFIXES
        ):
            return True
    return False
