import ntpath
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import LnkParse3


SHORTCUT_PARSER_VERSION = "lnkparse3-1.6"


class ShortcutParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedShortcut:
    target_path: str
    network_root: str | None
    mapped_device: str | None


def parse_shortcut(path: Path) -> ParsedShortcut:
    try:
        with path.open("rb") as stream, warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            payload = LnkParse3.lnk_file(stream, cp="cp932").get_json()
    except Exception as exc:
        raise ShortcutParseError(type(exc).__name__) from exc

    link_info = _mapping(payload.get("link_info"))
    location = _mapping(link_info.get("location_info"))
    data = _mapping(payload.get("data"))
    network_root = _text(
        location.get("net_name_unicode") or location.get("net_name")
    )
    mapped_device = _text(
        location.get("device_name_unicode") or location.get("device_name")
    )
    suffix = _text(
        link_info.get("common_path_suffix_unicode")
        or link_info.get("common_path_suffix")
    )
    local_base = _text(
        link_info.get("local_base_path_unicode")
        or link_info.get("local_base_path")
    )
    relative = _text(data.get("relative_path"))

    target = None
    if network_root:
        target = ntpath.join(network_root, suffix or "")
    elif local_base:
        target = ntpath.join(local_base, suffix or "")
    elif relative:
        target = ntpath.join(str(path.parent), relative)
    if not target:
        raise ShortcutParseError("target_missing")
    return ParsedShortcut(
        target_path=ntpath.normpath(target),
        network_root=network_root,
        mapped_device=mapped_device,
    )


def shortcut_semantic_text(
    relative_path: str,
    *,
    target_path: str | None,
    target_status: str,
    target_kind: str | None,
) -> str:
    values = [
        f"relative_path: {relative_path}",
        f"entry_type: windows_shortcut",
        f"shortcut_target_status: {target_status}",
    ]
    if target_path:
        values.append(f"shortcut_target_path: {target_path}")
    if target_kind:
        values.append(f"shortcut_target_kind: {target_kind}")
    return "\n".join(values)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.replace("\x00", "").strip()
    return normalized or None
