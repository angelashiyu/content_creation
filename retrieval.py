import re
from typing import List, Tuple
from chunking import chunk_document

DEFAULT_QUERY = "GenAI AI LLM marketing visibility SEO GEO"

_WORD = re.compile(r"[a-z0-9]+")

def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))

def retrieve_top_k(query: str, chunks: List[str], k: int = 6, tiebreak: str = "") -> List[str]:
    q = _tokens(query)
    if not q:
        return chunks[:k]
    tb = _tokens(tiebreak)

    scored: List[Tuple[int, int, int, str]] = []
    for i, ch in enumerate(chunks):
        t = _tokens(ch)
        score = len(q & t)  # overlap count
        scored.append((score, len(tb & t), i, ch))

    # sort: highest score first, then most tiebreak words, then original order
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))

    # keep non-zero matches; fallback to first k if none match
    top = [ch for score, _, _, ch in scored if score > 0][:k]
    return top if top else chunks[:k]

def build_context(document: str, query: str = DEFAULT_QUERY, k: int = 6) -> str:
    chunks = chunk_document(document, mode="paragraph", target_chars=500)
    # short topics like "AI SEO" tie on many chunks; brand terms pick among them
    return "\n\n---\n\n".join(retrieve_top_k(query, chunks, k=k, tiebreak=DEFAULT_QUERY))
