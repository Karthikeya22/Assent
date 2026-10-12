import itertools

from assent_retrieval.chunk import chunk_text
from assent_retrieval.search import rrf


def test_short_text_is_one_chunk_with_offset_zero() -> None:
    [c] = chunk_text("One sentence. Two sentences.")
    assert (c.text, c.char_offset) == ("One sentence. Two sentences.", 0)


def test_chunks_are_exact_slices_sentence_aligned_with_overlap() -> None:
    sents = [f"Sentence number {i} has exactly seven words." for i in range(40)]
    text = " ".join(sents)
    chunks = chunk_text(text, max_tokens=60, overlap=0.15)
    assert len(chunks) > 1
    for c in chunks:
        assert text[c.char_offset : c.char_offset + len(c.text)] == c.text  # exact slice
        assert c.text.startswith("Sentence number") and c.text.endswith(".")  # sentence aligned
    # Consecutive chunks overlap (the next one starts before the previous one ends).
    for a, b in itertools.pairwise(chunks):
        assert b.char_offset < a.char_offset + len(a.text)
    # Every sentence is covered.
    assert all(any(s in c.text for c in chunks) for s in sents)


def test_line_breaks_split_sentences() -> None:
    text = "Header line\nDate: 09/20/2026\nBody text here."
    chunks = chunk_text(text, max_tokens=3, overlap=0.0)
    assert [c.text for c in chunks] == ["Header line", "Date: 09/20/2026", "Body text here."]


def test_rrf_rewards_agreement_and_is_deterministic() -> None:
    fused = rrf([["a", "b", "c"], ["b", "a", "d"], ["b"]], k=60)
    assert fused[0] == "b"  # top in two lists, present in all three
    assert fused[1] == "a"
    assert set(fused) == {"a", "b", "c", "d"}
    assert rrf([["x", "y"], ["y", "x"]]) == ["x", "y"]  # ties break by first appearance
