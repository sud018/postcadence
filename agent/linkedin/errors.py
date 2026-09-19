"""Errors from talking to LinkedIn."""

class LinkedInError(RuntimeError):
    """Something went wrong calling the LinkedIn API."""


class LinkedInAuthError(LinkedInError):
    """The token is missing, expired, or rejected."""