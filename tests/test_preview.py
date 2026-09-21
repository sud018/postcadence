import pytest

from agent.preview import PreviewError, build_body, decide, extract_text, title_for


def body(text="Post body here."):
    return build_body("A topic", text, "09:00", "post", 30)


def test_body_round_trips_the_post():
    assert extract_text(body("Line one.\n\nLine two.")) == "Line one.\n\nLine two."


def test_edited_body_is_what_gets_extracted():
    edited = body("Original.").replace("Original.", "I fixed this sentence.")
    assert extract_text(edited) == "I fixed this sentence."


def test_missing_markers_is_an_error():
    with pytest.raises(PreviewError, match="markers"):
        extract_text("someone deleted the whole body")


def test_title_identifies_date_and_slot():
    assert title_for("2026-09-22", "09:00") == "Draft post for 2026-09-22 09:00"


@pytest.mark.parametrize("comments,expected", [
    ([], "none"),
    ([{"body": "nice one"}], "none"),
    ([{"body": "/approve"}], "approve"),
    ([{"body": "/cancel"}], "cancel"),
    ([{"body": "/approve"}, {"body": "/cancel changed my mind"}], "cancel"),
    ([{"body": "/cancel"}, {"body": "/approve after all"}], "approve"),
    ([{"body": "I would /approve this but not yet"}], "none"),
])
def test_decide_reads_the_newest_instruction(comments, expected):
    assert decide(comments) == expected
