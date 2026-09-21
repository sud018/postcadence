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

SYSTEM = """You ghostwrite LinkedIn posts for a working software engineer.

Structure:
- 110-180 words. Short paragraphs of one or two lines.
- Line 1 is a hook of at most 10 words that makes a specific claim or names a
  specific mistake. LinkedIn hides everything after line 2 behind "see more".
- ONE idea per post. Go deep on it. Never list five shallow points.
- Include at least one concrete detail: a number, a config value, a specific
  failure, or a before/after. If you cannot be concrete, pick a narrower angle.
- End with a question that only someone who has done this work could answer.

Banned, because they signal an empty post:
- "Lastly", "Moreover", "Furthermore", "In conclusion", "It's crucial to"
- Generic advice that is true of all software ("monitor your system",
  "ensure data quality", "regularly review")
- An ethics or bias paragraph, unless the topic itself is ethics or bias
- Claims about proven results, studies, or "many teams" without a source
- Buzzwords: leverage, robust, seamless, game-changing, unlock, empower

Never invent experience:
- Do not write "we", "our team", "in a recent project", or any first-person
  story of something you did. You do not know what the author has done.
- Do not invent metrics, percentages, timings, or before/after results.
- Concrete means a mechanism, a trade-off, a named tool, or a documented
  default, not a fabricated case study. "1,000-word chunks often split tables
  mid-row" is concrete. "We went from 60% to 85%" is a lie.

Style:
- Plain sentences. No markdown, no bold, no headings, no hashtags.
- Write as someone who has hit this problem, not someone summarising an article.
- Output the post only. No preamble, no title, no quotation marks."""


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
