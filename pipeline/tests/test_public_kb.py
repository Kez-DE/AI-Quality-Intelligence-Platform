"""Public KB for the customer assistant: retrieval and editing rules (data/public_kb)."""
from pathlib import Path

from agent import public_kb
from agent.knowledge_base import _parse_frontmatter, _tokenize

PUBLIC_KB = Path(__file__).resolve().parents[2] / "data" / "public_kb"


def _docs():
    return [f for f in sorted(PUBLIC_KB.glob("*.md")) if f.name != "README.md"]


def test_vietnamese_words_that_look_like_stopwords_survive():
    # "an" and "do" were English stopwords; they erased ăn, đồ, đỏ and "an toàn".
    assert _tokenize("đặt đồ ăn") == ["dat", "do", "an"]
    assert "an" in _tokenize("an toàn")
    assert "do" in _tokenize("vượt đèn đỏ")


def test_food_ordering_question_finds_the_food_section():
    top = public_kb.search_public_knowledge("đặt đồ ăn", top_k=1)
    assert top and "Food" in top[0]["heading"]


def test_every_public_doc_carries_its_source_and_no_markdown_bold():
    for f in _docs():
        meta, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
        assert meta.get("audience") == "public", f.name
        assert meta.get("source_url", "").startswith("https://"), f.name
        assert meta.get("source_checked_at"), f.name
        assert "**" not in body, f"{f.name}: the widgets show ** as-is"
