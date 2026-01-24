import re
from typing import List, Tuple

_WORD = re.compile(r"[a-z0-9]+")

def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))

def retrieve_top_k(query: str, chunks: List[str], k: int = 6) -> List[str]:
    q = _tokens(query)
    if not q:
        return chunks[:k]

    scored: List[Tuple[int, int, str]] = []
    for i, ch in enumerate(chunks):
        t = _tokens(ch)
        score = len(q & t)  # overlap count
        scored.append((score, i, ch))

    # sort: highest score first, stable by original order
    scored.sort(key=lambda x: (-x[0], x[1]))

    # keep non-zero matches; fallback to first k if none match
    top = [ch for score, _, ch in scored if score > 0][:k]
    return top if top else chunks[:k]