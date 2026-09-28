# Changelog

## 1.0.0 - the local app

Everything the command line did, now in your browser - plus the parts that used
to need a terminal.

- **Dashboard** with next post, streak, success rate, content runway, a 30-day
  activity chart and posts per time slot.
- **Setup in five steps:** writer (OpenAI, Anthropic, Gemini or Ollama, with the
  model list fetched live), LinkedIn sign-in, schedule builder, topics, GitHub.
- **Schedule builder** writes the UTC cron lines into `post.yml` itself, so the
  schedule and the workflow can no longer drift apart.
- **Drafts:** write a post, edit it beside a LinkedIn-style preview, then publish,
  skip or discard it.
- **GitHub from the browser:** device-flow sign-in, one-click push of settings,
  and secrets sealed with the repository's public key before they leave your PC.
- **Settings:** voice (tone and "about you"), connection status, health checks,
  and a sync badge that says whether GitHub is running what you see.
- **First run** on a fresh clone shows a welcome page instead of an error.
- `PostCadence.bat` - double-click to install and start on Windows.

## 0.1.0 - the agent

Command-line agent: topics from xlsx/docx/pdf/csv/txt, LLM writing, formatting,
LinkedIn posting, preview mode via GitHub Issues, and scheduling on GitHub Actions.
