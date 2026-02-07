"""Tests for configuration loading and validation."""

import pytest

from ll_uni_fan_linux.config import Config, _parse_channels


class TestConfigDefaults:
    def test_defaults(self) -> None:
        cfg = Config()
        assert cfg.profile == "balanced"
        assert cfg.poll_interval == 3.0
        assert cfg.log_level == "INFO"
        assert cfg.debug is False
        assert cfg.channels == (0, 1, 2, 3)
        assert cfg.safe_speed == 90.0
        assert cfg.protocol == "lian-li-sl-inf"

    def test_debug_forces_log_level(self) -> None:
        cfg = Config(debug=True)
        assert cfg.log_level == "DEBUG"


class TestConfigValidation:
    def test_invalid_profile_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid profile"):
            Config(profile="turbo")

    def test_zero_poll_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="Poll interval must be positive"):
            Config(poll_interval=0)

    def test_negative_poll_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="Poll interval must be positive"):
            Config(poll_interval=-1.0)

    def test_safe_speed_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="Safe speed must be 0-100"):
            Config(safe_speed=150.0)

    def test_invalid_protocol_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown protocol"):
            Config(protocol="nonexistent")


class TestParseChannels:
    def test_single_channel(self) -> None:
        assert _parse_channels("2") == (2,)

    def test_multiple_channels(self) -> None:
        assert _parse_channels("0,1,2") == (0, 1, 2)

    def test_deduplicates_and_sorts(self) -> None:
        assert _parse_channels("3,1,1,0") == (0, 1, 3)

    def test_invalid_channel_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_channels("5")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_channels("")


class TestConfigLoadCLI:
    def test_cli_profile(self) -> None:
        cfg = Config.load(["--profile", "silent"])
        assert cfg.profile == "silent"

    def test_cli_debug(self) -> None:
        cfg = Config.load(["--debug"])
        assert cfg.debug is True
        assert cfg.log_level == "DEBUG"

    def test_cli_poll_interval(self) -> None:
        cfg = Config.load(["--poll-interval", "5.0"])
        assert cfg.poll_interval == 5.0

    def test_cli_log_level(self) -> None:
        cfg = Config.load(["--log-level", "WARNING"])
        assert cfg.log_level == "WARNING"

    def test_cli_channels(self) -> None:
        cfg = Config.load(["--channels", "0,2"])
        assert cfg.channels == (0, 2)

    def test_cli_safe_speed(self) -> None:
        cfg = Config.load(["--safe-speed", "80"])
        assert cfg.safe_speed == 80.0

    def test_cli_protocol(self) -> None:
        cfg = Config.load(["--protocol", "lian-li-al-v1"])
        assert cfg.protocol == "lian-li-al-v1"

    def test_no_args_uses_defaults(self) -> None:
        cfg = Config.load([])
        assert cfg.profile == "balanced"


class TestConfigLoadEnvFile:
    def test_load_from_env_file(self, tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
        import ll_uni_fan_linux.config as config_mod

        env_file = tmp_path / "config"  # type: ignore[operator]
        env_file.write_text("PROFILE=performance\nPOLL_INTERVAL=5\nCHANNELS=0,1,2\nSAFE_SPEED=80\n")
        monkeypatch.setattr(config_mod, "DEFAULT_CONFIG_PATH", str(env_file))

        cfg = Config.load([])
        assert cfg.profile == "performance"
        assert cfg.poll_interval == 5.0
        assert cfg.channels == (0, 1, 2)
        assert cfg.safe_speed == 80.0

    def test_env_vars_override_file(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import ll_uni_fan_linux.config as config_mod

        env_file = tmp_path / "config"  # type: ignore[operator]
        env_file.write_text("PROFILE=silent\n")
        monkeypatch.setattr(config_mod, "DEFAULT_CONFIG_PATH", str(env_file))
        monkeypatch.setenv("PROFILE", "performance")

        cfg = Config.load([])
        assert cfg.profile == "performance"

    def test_empty_env_var_overrides_file(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty string in env var should still take priority over file."""
        import ll_uni_fan_linux.config as config_mod

        env_file = tmp_path / "config"  # type: ignore[operator]
        env_file.write_text("LOG_LEVEL=WARNING\n")
        monkeypatch.setattr(config_mod, "DEFAULT_CONFIG_PATH", str(env_file))
        monkeypatch.setenv("LOG_LEVEL", "")

        cfg = Config.load([])
        # Empty string from env var → .upper() → "" → invalid for logging,
        # but it should NOT fall through to file value "WARNING"
        assert cfg.log_level == ""

    def test_cli_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROFILE", "silent")
        cfg = Config.load(["--profile", "performance"])
        assert cfg.profile == "performance"
