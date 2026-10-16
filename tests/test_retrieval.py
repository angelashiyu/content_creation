from chunking import chunk_by_chars, chunk_by_paragraphs
from retrieval import build_context, retrieve_top_k


def test_paragraphs_merge_up_to_target_size():
    text = "a" * 200 + "\n\n" + "b" * 200 + "\n\n" + "c" * 200
    assert [len(c) for c in chunk_by_paragraphs(text, target_chars=500)] == [402, 200]


def test_single_newlines_are_not_paragraph_boundaries():
    # the bug where the whole Notion page became one chunk
    assert len(chunk_by_paragraphs("one\ntwo\nthree", target_chars=5)) == 1


def test_char_chunks_cut_at_fixed_size():
    assert chunk_by_chars("x" * 1100, size=500) == ["x" * 500, "x" * 500, "x" * 100]


def test_retrieval_drops_chunks_with_no_overlap():
    chunks = ["pricing plans", "brand visibility in ai answers", "ai seo checklist"]
    assert retrieve_top_k("ai visibility", chunks, k=6) == [chunks[1], chunks[2]]


def test_retrieval_ranks_by_overlap_then_page_order():
    chunks = ["ai", "ai seo", "seo"]
    assert retrieve_top_k("ai seo", chunks, k=2) == ["ai seo", "ai"]


def test_retrieval_falls_back_to_first_chunks_when_nothing_matches():
    assert retrieve_top_k("zebra", ["one", "two", "three"], k=2) == ["one", "two"]


def test_build_context_keeps_top_three_paragraph_chunks():
    page = "\n\n".join(f"topic{i} " + "filler " * 80 for i in range(5))
    context = build_context(page, query="topic0 topic1 topic2 topic3 topic4 filler")
    assert context.count("\n\n---\n\n") == 2
