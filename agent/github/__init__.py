"""Everything that talks to GitHub: signing in, pushing files, storing secrets."""
from agent.github.errors import GitHubAuthError, GitHubError

__all__ = ["GitHubError", "GitHubAuthError"]
