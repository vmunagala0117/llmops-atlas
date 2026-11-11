"""Rules knowledge base: one markdown file per reason code (spec 2.2).

Each file starts with YAML front matter between ``---`` lines, followed by a
markdown body with ``##`` sections. The rules are illustrative, not official
network rules.

A rules file is released once it is merged to main. To change one, bump its
``version`` and ``effective_date`` so later citations (``code@version``) stay
traceable.
"""

from pathlib import Path

import yaml

REQUIRED_KEYS = ("code", "title", "version", "owner", "effective_date", "review_by", "status")
CODE_SECTIONS = (
    "When it applies",
    "When it does not apply",
    "Evidence the analyst should request",
    "Time limits (illustrative)",
)


def _split_front_matter(text: str, name: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{name}: missing front matter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{name}: front matter is not closed")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{name}: front matter is not a mapping")
    return meta, text[end + len("\n---\n") :].strip()


def load_rules(path: str | Path) -> list[dict]:
    """Return one dict per ``*.md`` file in ``path``: front matter keys plus ``body`` and ``file``.

    Files are sorted by name so the order never depends on the file system.
    """
    rules = []
    for file in sorted(Path(path).glob("*.md")):
        meta, body = _split_front_matter(file.read_text(encoding="utf-8"), file.name)
        rules.append({**meta, "body": body, "file": file.name})
    return rules


def sections(body: str) -> dict[str, str]:
    """Split a markdown body into ``{heading: text}`` on ``## `` headings."""
    found: dict[str, str] = {}
    heading = None
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading is not None:
                found[heading] = "\n".join(lines).strip()
            heading, lines = line[3:].strip(), []
        elif heading is not None:
            lines.append(line)
    if heading is not None:
        found[heading] = "\n".join(lines).strip()
    return found
