"""Turning LinkedIn's errors into something a person can act on."""
from __future__ import annotations

import pytest
import requests

from agent.linkedin import diagnose
from agent.linkedin.diagnose import BAD, OK, UNKNOWN, WARN


class FakeResponse:
    def __init__(self, text="", status=200, location="", payload=None):
        self.text = text
        self.status_code = status
        self.headers = {"location": location} if location else {}
        self._payload = payload or {}

    def json(self):
        return self._payload


def answer(monkeypatch, response, verb="get"):
    monkeypatch.setattr(diagnose.requests, verb, lambda *a, **k: response)


def boom(*args, **kwargs):
    raise requests.ConnectionError("no network")


# --- the sign-in probe -----------------------------------------------------

def test_no_client_id_is_not_a_linkedin_problem():
    result = diagnose.probe_authorize("", "http://127.0.0.1:8787/cb")
    assert result.state == UNKNOWN
    assert "Paste it below" in result.fix


def test_unapproved_product_is_named(monkeypatch):
    answer(monkeypatch, FakeResponse(location="https://example/?error=unauthorized_scope_error"))
    result = diagnose.probe_authorize("id", "http://127.0.0.1:8787/cb")
    assert result.state == BAD
    assert "not allowed to post" in result.detail
    assert "Share on LinkedIn" in result.fix


def test_mismatched_redirect_is_named(monkeypatch):
    answer(monkeypatch, FakeResponse(text="The redirect_uri does not match the registered value"))
    result = diagnose.probe_authorize("id", "http://127.0.0.1:8787/cb")
    assert result.state == BAD
    assert "redirect URL" in result.detail


def test_unknown_client_id_is_named(monkeypatch):
    answer(monkeypatch, FakeResponse(text="error: invalid_client_id"))
    result = diagnose.probe_authorize("typo", "http://127.0.0.1:8787/cb")
    assert result.state == BAD
    assert "Client ID" in result.detail


def test_being_sent_to_the_login_page_means_all_is_well(monkeypatch):
    answer(monkeypatch, FakeResponse(status=302, location="https://www.linkedin.com/uas/login?..."))
    assert diagnose.probe_authorize("id", "http://127.0.0.1:8787/cb").state == OK


def test_the_login_page_itself_also_means_all_is_well(monkeypatch):
    answer(monkeypatch, FakeResponse(text="<html>Sign in to LinkedIn ... login form"))
    assert diagnose.probe_authorize("id", "http://127.0.0.1:8787/cb").state == OK


def test_no_internet_is_reported_as_unknown_not_broken(monkeypatch):
    monkeypatch.setattr(diagnose.requests, "get", boom)
    result = diagnose.probe_authorize("id", "http://127.0.0.1:8787/cb")
    assert result.state == UNKNOWN
    assert "internet" in result.fix


def test_the_most_specific_error_wins(monkeypatch):
    """A scope error also contains 'invalid_request'; the useful one must win."""
    answer(monkeypatch, FakeResponse(text="invalid_request ... unauthorized_scope_error"))
    assert "Share on LinkedIn" in diagnose.probe_authorize("id", "cb").fix


# --- the token check -------------------------------------------------------

def test_not_connected_yet_is_not_an_error():
    assert diagnose.check_token("", "id", "secret").state == UNKNOWN


def test_a_token_that_may_post_is_ok(monkeypatch):
    answer(monkeypatch, FakeResponse(payload={
        "active": True, "status": "active", "scope": "openid,profile,w_member_social"}), verb="post")
    result = diagnose.check_token("tok", "id", "secret")
    assert result.state == OK
    assert "allowed to post" in result.detail


def test_a_token_without_the_posting_scope_is_caught_early(monkeypatch):
    answer(monkeypatch, FakeResponse(payload={
        "active": True, "status": "active", "scope": "openid,profile"}), verb="post")
    result = diagnose.check_token("tok", "id", "secret")
    assert result.state == BAD
    assert "may not publish" in result.detail


def test_a_revoked_token_is_caught(monkeypatch):
    answer(monkeypatch, FakeResponse(payload={"active": False, "status": "revoked"}), verb="post")
    assert diagnose.check_token("tok", "id", "secret").state == BAD


def test_linkedin_refusing_to_describe_the_token_is_only_a_warning(monkeypatch):
    answer(monkeypatch, FakeResponse(status=400), verb="post")
    assert diagnose.check_token("tok", "id", "secret").state == WARN


@pytest.mark.parametrize("scope", ["w_member_social", "openid,profile,w_member_social"])
def test_scope_is_matched_anywhere_in_the_list(monkeypatch, scope):
    answer(monkeypatch, FakeResponse(payload={
        "active": True, "status": "active", "scope": scope}), verb="post")
    assert diagnose.check_token("tok", "id", "secret").state == OK
