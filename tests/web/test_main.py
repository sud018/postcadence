"""The port must be predictable: LinkedIn only accepts an exact redirect URL."""
from __future__ import annotations

import socket

import pytest

from web.__main__ import HOST, PORT, chosen_port, is_free


def test_default_port_when_no_override(monkeypatch):
    monkeypatch.delenv("POSTCADENCE_PORT", raising=False)
    assert chosen_port() == PORT


def test_env_var_overrides_for_one_run(monkeypatch):
    monkeypatch.setenv("POSTCADENCE_PORT", "9123")
    assert chosen_port() == 9123


def test_blank_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("POSTCADENCE_PORT", "   ")
    assert chosen_port() == PORT


def test_bad_env_var_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("POSTCADENCE_PORT", "eight thousand")
    with pytest.raises(SystemExit):
        chosen_port()


def test_is_free_sees_a_taken_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind((HOST, 0))
        taken = held.getsockname()[1]
        assert is_free(HOST, taken) is False
