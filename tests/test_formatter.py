import pytest

from agent.formatter import (MAX_LENGTH, fit_length, format_post, hashtags_for,
                             normalise_bullets, strip_markdown, tidy_spacing, unwrap_quotes)


def test_strips_markdown():
    out = strip_markdown("## Title\n**bold** and *italic* and __also bold__\n> quoted\n---")
    assert "#" not in out and "*" not in out and "_" not in out and ">" not in out
    assert "bold" in out and "italic" in out


def test_bullets_become_arrows():
    assert normalise_bullets("- one\n* two\n• three") == "→ one\n→ two\n→ three"


def test_spacing_collapses_blank_lines():
    assert tidy_spacing("a\n\n\n\n\nb   \n") == "a\n\nb"


def test_unwrap_quotes():
    assert unwrap_quotes('"the whole post"') == "the whole post"
    assert unwrap_quotes('He said "hi" to me') == 'He said "hi" to me'


def test_hashtags_prefer_acronyms_and_long_words():
    assert hashtags_for("Why RAG systems fail in production", "") == ["#RAG", "#Systems", "#Production"]


def test_hashtags_skip_ones_already_in_the_post():
    assert "#RAG" not in hashtags_for("Why RAG systems fail", "Great #rag content here")


def test_fit_length_cuts_at_a_boundary():
    text = ("Sentence one. " * 400).strip()
    out = fit_length(text)
    assert len(out) <= MAX_LENGTH
    assert out.endswith(".")
    assert "Sentenc." not in out       # never mid-word


def test_short_text_is_untouched_by_fit_length():
    assert fit_length("short post") == "short post"


def test_format_post_end_to_end():
    raw = '"## Draft\n\n**Most** RAG demos work.\n\n- chunking breaks\n\n\n\nWhat breaks for you?"'
    out = format_post(raw, "Why RAG systems fail in production")
    assert out.startswith("Draft")
    assert "→ chunking breaks" in out
    assert "\n\n\n" not in out
    assert out.endswith("#RAG #Systems #Production")
    assert len(out) <= MAX_LENGTH


def test_format_post_without_hashtags():
    out = format_post("Body only.", "Why RAG fails", add_hashtags=False)
    assert out == "Body only."
