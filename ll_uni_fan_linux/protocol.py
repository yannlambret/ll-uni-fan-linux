"""Fan controller protocol definitions.

Each Protocol instance encapsulates the USB identification and command format
for a specific controller model. Protocol data is loaded from protocols.yaml;
the active protocol is selected by name via the PROTOCOL config parameter.

Lian-Li protocol reverse-engineered from https://github.com/EightB1ts/uni-sync.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

_PROTOCOLS_FILE = Path(__file__).parent / "protocols.yaml"

DEFAULT_PROTOCOL_KEY = "lian-li-sl-inf"


@dataclass(frozen=True)
class Protocol:
    """USB HID protocol definition for a fan controller model."""

    name: str
    vendor_id: int
    product_id: int

    # Command bytes
    cmd_prefix: int
    sub_cmd: int
    init_byte: int
    mode_byte: int
    speed_channel_base: int

    # Speed conversion: byte = int((rpm_min + rpm_scale * speed%) / rpm_divisor)
    rpm_min: float
    rpm_scale: float
    rpm_divisor: float

    # Inter-command delays (seconds)
    delay_init: float
    delay_mode: float
    delay_speed: float

    def speed_to_byte(self, speed_percent: float) -> int:
        """Convert a speed percentage (0-100) to the controller byte value."""
        clamped = max(0.0, min(100.0, speed_percent))
        return int((self.rpm_min + self.rpm_scale * clamped) / self.rpm_divisor)

    def build_init(self) -> list[int]:
        """Build the initialization command (no RGB sync)."""
        return [self.cmd_prefix, self.sub_cmd, self.init_byte, 0x00, 0x00, 0x00, 0x00]

    def build_mode(self, channel: int) -> list[int]:
        """Build the manual mode command for a channel."""
        return [self.cmd_prefix, self.sub_cmd, self.mode_byte, 0x10 << channel]

    def build_speed(self, channel: int, speed_percent: float) -> list[int]:
        """Build the speed command for a channel."""
        return [self.cmd_prefix, self.speed_channel_base + channel, 0x00,
                self.speed_to_byte(speed_percent)]


def _load_all() -> dict[str, dict]:
    """Load raw protocol definitions from YAML."""
    with open(_PROTOCOLS_FILE) as f:
        return yaml.safe_load(f)


def available_protocols() -> list[str]:
    """Return the list of available protocol keys."""
    return list(_load_all().keys())


def load_protocol(key: str) -> Protocol:
    """Load a Protocol instance by key from protocols.yaml.

    Raises KeyError if the key is not found.
    """
    protocols = _load_all()
    if key not in protocols:
        available = ", ".join(sorted(protocols.keys()))
        raise KeyError(f"Unknown protocol '{key}'. Available: {available}")
    return Protocol(**protocols[key])
