"""The cron in post.yml must match what the config implies.

Both sides are read from the repository by name. tests/conftest.py points
load_config() at a throwaway config, which is right for every other test and
wrong for this one: it would compare the real post.yml against a fake config.
"""
import re

import pytest

from agent import paths
from agent.config import load_config
from agent.schedule import cron_lines

WORKFLOW = paths.ROOT / ".github" / "workflows" / "post.yml"
CONFIG = paths.ROOT / "data" / "config.json"
CRON_LINE = re.compile(r'- cron:\s*"([^"]+)"')


@pytest.mark.skipif(not CONFIG.exists(), reason="no config yet - nothing to drift from")
def test_workflow_cron_matches_config():
    in_file = set(CRON_LINE.findall(WORKFLOW.read_text(encoding="utf-8")))
    expected = set(cron_lines(load_config(CONFIG)))     # the real file, not the sandbox

    assert in_file == expected, (
        f"post.yml has {sorted(in_file)}, config needs {sorted(expected)}. "
        "Open the app, go to Setup - Schedule and press Save to rewrite post.yml."
    )
