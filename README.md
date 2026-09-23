# PostCadence

*Your ideas, posted on schedule.*

An agent that writes and publishes LinkedIn posts from a list of topics. It runs
on GitHub Actions, so nothing needs to be open on your machine.

```
topic  ->  LLM writes  ->  formatter cleans  ->  LinkedIn  ->  history
```

## How it works

| Piece | File | Job |
|---|---|---|
| Settings | `agent/config.py` → `data/config.json` | provider, times, timezone, tone |
| Memory | `agent/state.py` → `data/state.json` | next topic, post history |
| Secrets | `agent/secrets_store.py` | env var first, then OS keyring |
| LLM | `agent/llm/` | one `generate(prompt)` behind any provider |
| LinkedIn | `agent/linkedin/` | OAuth sign-in, posting |
| Topics | `agent/topics/` | load from xlsx/docx/pdf/csv/txt, pick per slot |
| Writing | `agent/writer.py` | prompt building |
| Formatting | `agent/formatter.py` | strip markdown, bullets, hashtags, 3000-char limit |
| Scheduling | `agent/schedule.py` | which slots are due, in your timezone |
| Preview | `agent/preview.py` | draft posts as GitHub Issues for approval |
| Pipeline | `agent/run.py` | pick → write → format → post → record |

## Setup

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt

python -m agent init                  # create data/config.json and data/state.json

python -m agent secret set OPENAI_API_KEY
python -m agent secret set LINKEDIN_CLIENT_ID
python -m agent secret set LINKEDIN_CLIENT_SECRET
python -m agent linkedin connect      # browser sign-in, stores the access token

python -m agent topics add --file topics.xlsx
python -m agent run --dry-run         # generate a post without publishing
```

To run it in the cloud:

```bash
python -m agent secret push           # upload keys to GitHub Actions secrets
python -m agent cron                  # print the cron lines for your schedule
# paste them into .github/workflows/post.yml, then commit and push
```

## Commands

| Command | Does |
|---|---|
| `python -m agent status` | next run, topics left, recent posts, token expiry |
| `python -m agent show` | config, state and masked secrets |
| `python -m agent run [--dry-run] [--slot HH:MM] [--force]` | one post |
| `python -m agent run-due [--dry-run]` | whatever is due now (used by the scheduler) |
| `python -m agent topics add --file F \| --text "a; b"` | add topics |
| `python -m agent topics list \| next \| clear` | inspect or reset topics |
| `python -m agent linkedin connect \| test-post` | sign in, or post a one-off |
| `python -m agent check-llm` | verify the API key works |
| `python -m agent token-check [--days N]` | days left on the LinkedIn token |
| `python -m agent secret set \| delete \| push` | manage credentials |
| `python -m agent cron` | cron lines for the current schedule |

## Settings (`data/config.json`)

| Key | Meaning |
|---|---|
| `llm_provider` / `llm_model` | `openai`, `anthropic`, `gemini`, `ollama` |
| `timezone` | IANA name, e.g. `America/Los_Angeles` |
| `posts_per_day` / `post_times` | how many and at what local times |
| `tone` | `professional`, `casual`, `storytelling` |
| `author_context` | facts about you the model may draw on |
| `mode` | `auto` posts directly; `preview` opens a draft issue first |
| `preview_minutes` | how long before the slot the draft appears |
| `preview_timeout_action` | `post` or `skip` when you do not respond |
| `catch_up_hours` | how long after a missed slot it may still post |

## Workflows

| File | Trigger | Does |
|---|---|---|
| `post.yml` | cron + manual | writes and publishes, commits state back |
| `ci.yml` | push, pull request | ruff + pytest on Python 3.10/3.11/3.12 |
| `token.yml` | Mondays | opens an issue when the token is nearly expired |

Cron is UTC and ignores daylight saving, so `python -m agent cron` emits one line
per slot per offset. Runs that are not due exit in seconds.

## Preview mode

With `"mode": "preview"`, a draft opens as a GitHub Issue `preview_minutes` before
the slot. Comment `/approve` to publish, `/cancel` to skip, or edit the text
between the markers and it publishes as edited. Silence falls back to
`preview_timeout_action`.

## Maintenance

- **The LinkedIn token lasts 60 days.** `token.yml` opens a reminder issue two
  weeks out. To renew: `python -m agent linkedin connect`, then
  `python -m agent secret push`, then commit the updated `data/config.json`.
- **The LinkedIn API version** in `agent/linkedin/poster.py` is supported for
  about a year. A `426 NONEXISTENT_VERSION` error means bump `LINKEDIN_VERSION`.
- **Topics run out** and then repeat the previous day's with a fresh angle. Add
  more any time; the bookmark picks them up automatically.

## Tests

```bash
python -m pytest -q
ruff check .
```

Nothing in the test suite touches the network, LinkedIn, or your real config.
