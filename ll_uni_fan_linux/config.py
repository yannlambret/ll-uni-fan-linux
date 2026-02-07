"""Configuration parsing from /etc/default/ll-uni-fan-linux and CLI arguments."""

import argparse
import logging
import os
from dataclasses import dataclass

from dotenv import dotenv_values

from ll_uni_fan_linux.protocol import DEFAULT_PROTOCOL_KEY, available_protocols

DEFAULT_CONFIG_PATH = "/etc/default/ll-uni-fan-linux"
VALID_PROFILES = ("silent", "balanced", "performance")
ALL_CHANNELS = (0, 1, 2, 3)


def _parse_channels(raw: str) -> tuple[int, ...]:
    """Parse a comma-separated list of channel numbers (0-3)."""
    channels = tuple(sorted(set(int(c.strip()) for c in raw.split(","))))
    if not channels or any(c < 0 or c > 3 for c in channels):
        raise ValueError(f"Invalid channels: {raw}. Must be comma-separated values in 0-3")
    return channels


def _parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="ll-uni-fan-linux",
        description="Lian-Li UNI FAN SL-INF 120 Linux controller",
    )
    parser.add_argument(
        "--profile",
        choices=VALID_PROFILES,
        help="Fan profile (overrides config file)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        help="Temperature polling interval in seconds",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log level (overrides config file)",
    )
    parser.add_argument(
        "--channels",
        help="Comma-separated fan channels to control (0-3)",
    )
    parser.add_argument(
        "--safe-speed",
        type=float,
        help="Fan speed to set on daemon shutdown (0-100%%)",
    )
    parser.add_argument(
        "--protocol",
        help="Fan controller protocol key (see protocols.yaml)",
    )
    return parser.parse_args(argv)


@dataclass
class Config:
    """Daemon configuration."""

    profile: str = "balanced"
    poll_interval: float = 3.0
    log_level: str = "INFO"
    debug: bool = False
    channels: tuple[int, ...] = ALL_CHANNELS
    safe_speed: float = 90.0
    protocol: str = DEFAULT_PROTOCOL_KEY

    def __post_init__(self) -> None:
        if self.profile not in VALID_PROFILES:
            raise ValueError(
                f"Invalid profile '{self.profile}'. Must be one of: {', '.join(VALID_PROFILES)}"
            )

        if self.poll_interval <= 0:
            raise ValueError(f"Poll interval must be positive, got {self.poll_interval}")

        if not (0 <= self.safe_speed <= 100):
            raise ValueError(f"Safe speed must be 0-100, got {self.safe_speed}")

        valid_protocols = available_protocols()
        if self.protocol not in valid_protocols:
            raise ValueError(
                f"Unknown protocol '{self.protocol}'. "
                f"Available: {', '.join(sorted(valid_protocols))}"
            )

        if self.debug:
            self.log_level = "DEBUG"

    @classmethod
    def load(cls, argv: list[str] | None = None) -> "Config":
        """Load configuration from environment file, env vars, and CLI args.

        Priority (highest to lowest):
        1. CLI arguments
        2. Environment variables (set by systemd EnvironmentFile)
        3. /etc/default/ll-uni-fan-linux file
        4. Dataclass defaults
        """
        file_env = {k: v for k, v in dotenv_values(DEFAULT_CONFIG_PATH).items() if v is not None}

        def env(key: str) -> str | None:
            if key in os.environ:
                return os.environ[key]
            return file_env.get(key)

        kwargs: dict[str, object] = {}

        if (v := env("PROFILE")) is not None:
            kwargs["profile"] = v.lower()

        if (v := env("POLL_INTERVAL")) is not None:
            try:
                kwargs["poll_interval"] = float(v)
            except ValueError:
                pass

        if (v := env("LOG_LEVEL")) is not None:
            kwargs["log_level"] = v.upper()

        if (v := env("DEBUG")) is not None:
            kwargs["debug"] = v.lower() in ("true", "1", "yes")

        if (v := env("CHANNELS")) is not None:
            try:
                kwargs["channels"] = _parse_channels(v)
            except ValueError:
                pass

        if (v := env("SAFE_SPEED")) is not None:
            try:
                kwargs["safe_speed"] = float(v)
            except ValueError:
                pass

        if (v := env("PROTOCOL")) is not None:
            kwargs["protocol"] = v.lower()

        # CLI arguments override everything
        args = _parse_cli_args(argv)

        if args.profile is not None:
            kwargs["profile"] = args.profile

        if args.poll_interval is not None:
            kwargs["poll_interval"] = args.poll_interval

        if args.log_level is not None:
            kwargs["log_level"] = args.log_level

        if args.debug is True:
            kwargs["debug"] = True

        if args.channels is not None:
            kwargs["channels"] = _parse_channels(args.channels)

        if args.safe_speed is not None:
            kwargs["safe_speed"] = args.safe_speed

        if args.protocol is not None:
            kwargs["protocol"] = args.protocol.lower()

        return cls(**kwargs)

    def setup_logging(self) -> None:
        """Configure logging based on this config."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
