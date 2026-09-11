import re
from pathlib import Path

READABLE = {
    ".py", ".md", ".rst", ".txt", ".toml", ".cfg", ".yaml", ".yml",
    ".json", ".html", ".js", ".ts", ".css", ".sh", ".gitignore", ".env",
}


def _resolve(root: str, path: str) -> Path:
    r = Path(root).resolve()
    t = (r / path).resolve()
    t.relative_to(r)
    return t


def list_directory(root: str, path: str) -> str:
    try:
        t = _resolve(root, path)
    except ValueError:
        return "error: path outside repo"

    if not t.exists():
        return f"error: '{path}' not found"
    if t.is_file():
        return f"'{path}' is a file, use read_file"

    r = Path(root).resolve()
    out = []
    for e in sorted(t.iterdir(), key=lambda p: (p.is_file(), p.name)):
        tag = "dir" if e.is_dir() else "   "
        out.append(f"{tag}  {e.relative_to(r)}")
    return "\n".join(out) if out else "(empty)"


def read_file(root: str, path: str) -> str:
    try:
        t = _resolve(root, path)
    except ValueError:
        return "error: path outside repo"

    if not t.exists():
        return f"error: '{path}' not found"
    if t.is_dir():
        return f"'{path}' is a directory, use list_directory"
    if t.stat().st_size > 80_000:
        return f"error: file too large, use grep_search to find specific content"

    text = t.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > 300:
        return "\n".join(lines[:300]) + f"\n\n[truncated — {len(lines)} lines total]"
    return text


def grep_search(root: str, pattern: str, path: str = ".") -> str:
    try:
        t = _resolve(root, path)
    except ValueError:
        return "error: path outside repo"

    if not t.exists():
        return f"error: '{path}' not found"

    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"error: bad pattern — {e}"

    r = Path(root).resolve()
    files = [t] if t.is_file() else [
        p for p in sorted(t.rglob("*"))
        if p.is_file()
        and p.suffix in READABLE
        and not any(part.startswith(".") for part in p.relative_to(r).parts)
    ]

    hits = []
    for f in files:
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f.relative_to(r)}:{i}: {line.strip()}")
                    if len(hits) >= 50:
                        hits.append("[stopped at 50 results]")
                        return "\n".join(hits)
        except Exception:
            continue

    return "\n".join(hits) if hits else f"no matches for '{pattern}'"
