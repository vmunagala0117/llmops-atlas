"""Split rules files into retrievable chunks, one per ``##`` section (spec 2.4)."""

import hashlib

from atlas.corpus import sections


def content_hash(code: str, version: str, section: str, text: str) -> str:
    """sha256 over everything that makes a chunk citable, so a version bump is a new chunk."""
    joined = "\n".join([code, version, section, text])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def chunk_rules(docs: list[dict]) -> list[dict]:
    """Return one chunk per non-empty ``##`` section of each doc from ``load_rules``.

    The chunk text repeats the doc title and section heading, so it still makes
    sense on its own once it is retrieved without its file.
    """
    chunks = []
    for doc in docs:
        for section, body in sections(doc["body"]).items():
            if not body:
                continue
            text = f"# {doc['title']}\n## {section}\n\n{body}"
            chunks.append(
                {
                    "code": doc["code"],
                    "title": doc["title"],
                    "section": section,
                    "version": doc["version"],
                    "text": text,
                    "content_hash": content_hash(doc["code"], doc["version"], section, text),
                }
            )
    return chunks
