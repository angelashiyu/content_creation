import re
from typing import List

def chunk_by_chars(text: str, size: int = 500) -> List[str]:
    text = text.strip()
    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]

def chunk_by_paragraphs(text: str, target_chars: int = 500) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= target_chars:
            buf += "\n\n" + p
        else:
            chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks

def chunk_by_sentences(text: str, sentences_per_chunk: int = 4) -> List[str]:
    # simple sentence splitter; good enough for now
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    chunks = []
    for i in range(0, len(sents), sentences_per_chunk):
        chunk = " ".join(sents[i:i+sentences_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks

def chunk_document(text: str, mode: str = "paragraph", **kwargs) -> List[str]:
    if mode == "chars":
        return chunk_by_chars(text, size=kwargs.get("size", 500))
    if mode == "paragraph":
        return chunk_by_paragraphs(text, target_chars=kwargs.get("target_chars", 500))
    if mode == "sentences":
        return chunk_by_sentences(text, sentences_per_chunk=kwargs.get("sentences_per_chunk", 4))
    raise ValueError("mode must be one of: chars, paragraph, sentences")