"""Errors from talking to GitHub."""


class GitHubError(RuntimeError):
    """Something went wrong calling the GitHub API."""


class GitHubAuthError(GitHubError):
    """The token is missing, expired, or lacks the scope we need."""
