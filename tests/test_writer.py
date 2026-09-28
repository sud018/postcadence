"""The prompt the model receives - what goes in decides what comes out."""
from __future__ import annotations

from agent.config import Config
from agent.topics.picker import Pick
from agent.writer import build_prompt

FRESH = Pick(topic="Why cron runs in UTC", is_repeat=False, index=0)


def test_topic_and_tone_are_always_there():
    prompt = build_prompt(FRESH, Config(tone="casual"))
    assert "Why cron runs in UTC" in prompt
    assert "Conversational" in prompt


def test_author_context_reaches_the_model():
    prompt = build_prompt(FRESH, Config(author_context="Backend engineer, 8 years in fintech."))
    assert "Backend engineer, 8 years in fintech." in prompt
    assert "never invent" in prompt


def test_blank_author_context_adds_nothing():
    assert "About the author" not in build_prompt(FRESH, Config(author_context="   "))


def test_a_repeat_asks_for_a_new_angle():
    repeat = Pick(topic="Why cron runs in UTC", is_repeat=True, index=5)
    assert "different angle" in build_prompt(repeat, Config())


def test_recent_topics_are_listed_to_avoid():
    prompt = build_prompt(FRESH, Config(), recent_topics=["Retries", "Timeouts"])
    assert "Retries; Timeouts" in prompt
