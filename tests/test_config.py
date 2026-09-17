import pytest

from agent.config import Config, ConfigError, load_config, save_config


def test_default_config_is_valid():
    Config().validate()


def test_times_must_match_posts_per_day():
    with pytest.raises(ConfigError, match="must equal posts_per_day"):
        Config(posts_per_day=2, post_times=["09:00"]).validate()


@pytest.mark.parametrize("bad", ["9:00", "24:00", "12:60", "noon"])
def test_bad_time_format(bad):
    with pytest.raises(ConfigError, match="HH:MM"):
        Config(post_times=[bad]).validate()


def test_bad_timezone():
    with pytest.raises(ConfigError, match="timezone"):
        Config(timezone="Mars/Olympus").validate()


def test_round_trip_sorts_times(tmp_path):
    path = tmp_path / "config.json"
    save_config(Config(posts_per_day=2, post_times=["17:30", "09:00"]), path)
    assert load_config(path).post_times == ["09:00", "17:30"]
