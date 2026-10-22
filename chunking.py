import re


def chunk_by_chars(text, size=500):
    text = text.strip()
    chunks = []
    for start in range(0, len(text), size):
        piece = text[start:start + size]
        if piece.strip():
            chunks.append(piece)
    return chunks


def chunk_by_paragraphs(text, target_chars=500):
    # paragraphs are separated by a blank line
    paragraphs = []
    for p in re.split(r"\n\s*\n", text):
        if p.strip():
            paragraphs.append(p.strip())

    # join paragraphs together until the next one would make the chunk too long
    chunks = []
    current = ""
    for p in paragraphs:
        if current == "":
            current = p
        elif len(current) + 2 + len(p) <= target_chars:
            current = current + "\n\n" + p
        else:
            chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    return chunks


def chunk_by_sentences(text, sentences_per_chunk=4):
    # split after . ! or ? followed by a space
    sentences = []
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if s.strip():
            sentences.append(s.strip())

    chunks = []
    for start in range(0, len(sentences), sentences_per_chunk):
        chunk = " ".join(sentences[start:start + sentences_per_chunk]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def chunk_document(text, mode="paragraph", **options):
    if mode == "chars":
        return chunk_by_chars(text, size=options.get("size", 500))
    if mode == "paragraph":
        return chunk_by_paragraphs(text, target_chars=options.get("target_chars", 500))
    if mode == "sentences":
        return chunk_by_sentences(text, sentences_per_chunk=options.get("sentences_per_chunk", 4))
    raise ValueError("mode must be one of: chars, paragraph, sentences")
