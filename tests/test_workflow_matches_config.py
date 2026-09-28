"""The cron in post.yml must match what the config implies."""
import re

from agent import paths
from agent.config import load_config
from agent.schedule import cron_lines

WORKFLOW = paths.ROOT / ".github" / "workflows" / "post.yml"
CRON_LINE = re.compile(r'- cron:\s*"([^"]+)"')


def test_workflow_cron_matches_config():
    in_file = set(CRON_LINE.findall(WORKFLOW.read_text(encoding="utf-8")))
    expected = set(cron_lines(load_config()))

    assert in_file == expected, (
        f"post.yml has {sorted(in_file)}, config needs {sorted(expected)}. "
        "Run: python -m agent cron and paste the lines into post.yml."
    )
