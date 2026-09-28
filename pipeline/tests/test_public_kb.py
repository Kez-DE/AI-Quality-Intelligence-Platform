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


def test_seat_counts_become_one_token_and_lone_digits_stay_out():
    assert "7cho" in _tokenize("có xe 7 chỗ không")
    # A lone digit would tie "quận 7" to the "7 chỗ" heading.
    assert "7" not in _tokenize("gửi hàng sang quận 7")


def test_food_ordering_question_finds_the_food_section():
    top = public_kb.search_public_knowledge("đặt đồ ăn", top_k=1)
    assert top and "Food" in top[0]["heading"]


def test_questions_from_the_chat_battery_find_their_section():
    # Real customer wording that missed before (2026-09-28 battery). The chat
    # passes the top 3 chunks to the model, so that is what must hold.
    for query, heading_part in [
        ("có xe 7 chỗ không", "Limo"),
        ("gọi 19002088 được không", "1900 2088"),
        ("gửi hàng từ quận 1 sang quận 7 được không", "giao hàng"),
    ]:
        top = public_kb.search_public_knowledge(query, top_k=3)
        assert any(heading_part in c["heading"] for c in top), (query, [c["heading"] for c in top])


def test_every_public_doc_carries_its_source_and_no_markdown_bold():
    for f in _docs():
        meta, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
        assert meta.get("audience") == "public", f.name
        assert meta.get("source_url", "").startswith("https://"), f.name
        assert meta.get("source_checked_at"), f.name
        assert "**" not in body, f"{f.name}: the widgets show ** as-is"
