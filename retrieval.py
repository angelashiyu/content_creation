import re
from chunking import chunk_document

# brand words, used to choose between chunks that match the topic equally well
DEFAULT_QUERY = "GenAI AI LLM marketing visibility SEO GEO"


def get_words(text):
    # lowercase words and numbers, e.g. "AI-SEO tips!" -> {"ai", "seo", "tips"}
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_top_k(query, chunks, k=6, tiebreak=""):
    query_words = get_words(query)
    tiebreak_words = get_words(tiebreak)

    scored = []
    for chunk in chunks:
        chunk_words = get_words(chunk)
        score = len(query_words & chunk_words)  # how many query words the chunk contains
        if score > 0:
            bonus = len(tiebreak_words & chunk_words)
            scored.append({"chunk": chunk, "score": score, "bonus": bonus})

    if not scored:
        return chunks[:k]  # nothing matched, so use the start of the page

    # best score first, then the most brand words; equal chunks keep their page order
    scored.sort(key=lambda c: (c["score"], c["bonus"]), reverse=True)
    return [c["chunk"] for c in scored[:k]]


def build_context(document, query=DEFAULT_QUERY, k=6):
    chunks = chunk_document(document, mode="paragraph", target_chars=500)
    top_chunks = retrieve_top_k(query, chunks, k=k, tiebreak=DEFAULT_QUERY)
    return "\n\n---\n\n".join(top_chunks)
