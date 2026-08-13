from functools import lru_cache

from opencc import OpenCC


@lru_cache(maxsize=1)
def _simplified_to_traditional() -> OpenCC:
    return OpenCC("s2t.json")


@lru_cache(maxsize=1)
def _traditional_to_japanese() -> OpenCC:
    return OpenCC("t2jp.json")


def multilingual_query_variants(query: str) -> tuple[str, ...]:
    value = query.strip().casefold()
    if not value:
        return ()
    traditional = _simplified_to_traditional().convert(value)
    japanese = _traditional_to_japanese().convert(traditional)
    return tuple(dict.fromkeys((value, traditional, japanese)))
