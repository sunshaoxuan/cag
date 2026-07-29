import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import quote, unquote, urlsplit, urlunsplit


def build_resource_uri(
    *,
    source_type: str,
    location: str,
    reference: str | None,
    subpath: str | None,
    source_commit: str | None,
    document_path: str,
) -> str:
    relative_path = _join_relative_path(subpath, document_path)
    if source_type in {"local_directory", "network_share"}:
        return _file_uri(location, relative_path)
    if source_type == "svn":
        return _repository_uri(location, relative_path)
    if source_type in {"git", "gitlab"}:
        revision = source_commit or reference or "HEAD"
        web_base = _git_web_base(location, source_type)
        if web_base is not None:
            marker = "/-/blob/" if source_type == "gitlab" else "/blob/"
            return (
                f"{web_base}{marker}{quote(revision, safe='')}/"
                f"{quote(relative_path, safe='/')}"
            )
        if _looks_like_local_path(location):
            return _file_uri(location, relative_path)
        separator = "&" if "#" in location else "#"
        return (
            f"{location}{separator}revision={quote(revision, safe='')}"
            f"&path={quote(relative_path, safe='/')}"
        )
    return _repository_uri(location, relative_path)


def _join_relative_path(subpath: str | None, document_path: str) -> str:
    parts: list[str] = []
    for value in (subpath, document_path):
        if not value:
            continue
        parts.extend(
            part
            for part in PurePosixPath(value.replace("\\", "/")).parts
            if part not in {"", "."}
        )
    return "/".join(parts)


def _file_uri(location: str, relative_path: str) -> str:
    parsed = urlsplit(location)
    if parsed.scheme == "file":
        decoded_path = unquote(parsed.path)
        if parsed.netloc:
            windows_path = decoded_path.replace("/", "\\")
            location = f"\\\\{parsed.netloc}{windows_path}"
        elif re.match(r"^/[A-Za-z]:/", decoded_path):
            location = decoded_path[1:]
        else:
            location = decoded_path
    if re.match(r"^[A-Za-z]:[\\/]", location) or location.startswith("\\\\"):
        root = PureWindowsPath(location)
        target = root.joinpath(*PurePosixPath(relative_path).parts)
        return target.as_uri()
    root = Path(location).expanduser()
    target = root.joinpath(*PurePosixPath(relative_path).parts)
    return target.resolve(strict=False).as_uri()


def _repository_uri(location: str, relative_path: str) -> str:
    parsed = urlsplit(location)
    if parsed.scheme in {"http", "https", "svn", "svn+ssh", "file"}:
        path = f"{parsed.path.rstrip('/')}/{quote(relative_path, safe='/')}"
        return urlunsplit(
            (parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)
        )
    return (
        f"{location.rstrip('/')}/{quote(relative_path, safe='/')}"
        if relative_path
        else location
    )


def _git_web_base(location: str, source_type: str) -> str | None:
    parsed = urlsplit(location)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        if source_type != "gitlab" and parsed.netloc.casefold() != "github.com":
            return None
        path = parsed.path.removesuffix(".git").rstrip("/")
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    ssh = re.match(
        r"^(?:ssh://)?(?:[^@/\s]+@)?(?P<host>[^:/\s]+)[:/](?P<path>.+)$",
        location,
    )
    if ssh is None:
        return None
    host = ssh.group("host")
    if "." not in host or (
        source_type != "gitlab" and host.casefold() != "github.com"
    ):
        return None
    path = ssh.group("path").removesuffix(".git").strip("/")
    return f"https://{host}/{path}"


def _looks_like_local_path(location: str) -> bool:
    parsed = urlsplit(location)
    return (
        parsed.scheme == "file"
        or location.startswith(("/", "\\\\"))
        or re.match(r"^[A-Za-z]:[\\/]", location) is not None
    )
