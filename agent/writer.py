"""Turn a topic into raw post text using the configured LLM."""
from __future__ import annotations

from agent.config import Config
from agent.llm import get_provider
from agent.topics.picker import Pick

TONE_NOTES = {
    "professional": "Direct and credible. Concrete over clever. No hype words.",
    "casual": "Conversational, first person, like explaining to a colleague.",
    "storytelling": "Open with a specific moment or example, then draw the lesson.",
}

SYSTEM = """You ghostwrite LinkedIn posts for a software practitioner.

Rules:
- 120-220 words. Short paragraphs, one or two lines each.
- Open with a hook of at most 12 words that works alone, because LinkedIn hides the rest behind "see more".
- Be specific: numbers, trade-offs, things that actually break. No motivational filler.
- Never invent statistics, client names, or events that did not happen.
- Plain sentences. No markdown, no bold, no headings.
- End with one short question or a concrete takeaway.
- Do not add hashtags; they are added separately.
- Write the post only. No preamble, no title, no quotation marks around it."""


def build_prompt(pick: Pick, cfg: Config, recent_topics: list[str] | None = None) -> str:
    parts = [f"Write a LinkedIn post about: {pick.topic}", f"Tone: {TONE_NOTES.get(cfg.tone, '')}"]

    if pick.is_repeat:
        parts.append(
            "You have posted about this topic before, so take a clearly different angle: "
            "a different sub-problem, a different example, or the opposite side of the trade-off."
        )
    if recent_topics:
        parts.append("Recent posts covered: " + "; ".join(recent_topics) + ". Do not repeat those points.")

    return "\n\n".join(p for p in parts if p)


def write_post(pick: Pick, cfg: Config, recent_topics: list[str] | None = None) -> str:
    provider = get_provider(cfg)
    return provider.generate(build_prompt(pick, cfg, recent_topics), system=SYSTEM, max_tokens=700)
