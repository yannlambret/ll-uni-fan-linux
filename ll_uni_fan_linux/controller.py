"""Generic USB HID fan controller."""

import logging
import time

import hid

from ll_uni_fan_linux.protocol import Protocol

log = logging.getLogger(__name__)


class Controller:
    """Manages USB HID communication with a fan controller.

    Protocol-agnostic: all device-specific logic is delegated to the Protocol.
    """

    def __init__(self, protocol: Protocol) -> None:
        self._protocol = protocol
        self._device: hid.device | None = None
        self._device_path: bytes | None = None
        self._initialized: bool = False

    @property
    def connected(self) -> bool:
        return self._device is not None

    def find_and_open(self) -> bool:
        """Find the controller and open a connection."""
        if self._device is not None:
            return True

        for info in hid.enumerate(self._protocol.vendor_id, self._protocol.product_id):
            path = info["path"]
            try:
                dev = hid.device()
                dev.open_path(path)
                self._device = dev
                self._device_path = path
                self._initialized = False
                log.info(
                    "Connected to %s at %s (S/N: %s)",
                    self._protocol.name,
                    path.decode(errors="replace"),
                    info.get("serial_number", "N/A"),
                )
                return True
            except OSError as e:
                log.warning("Failed to open device at %s: %s", path.decode(errors="replace"), e)

        return False

    def close(self) -> None:
        """Close the connection to the controller."""
        if self._device is not None:
            try:
                self._device.close()
            except OSError:
                pass
            self._device = None
            self._device_path = None
            self._initialized = False
            log.info("Controller connection closed")

    def _write(self, data: list[int]) -> None:
        """Write data to the HID device. Raises OSError on failure."""
        if self._device is None:
            raise OSError("Controller not connected")
        self._device.write(bytes(data))

    def initialize(self, channels: tuple[int, ...]) -> None:
        """Send init + manual mode commands. Called once after connection.

        Raises OSError if the controller is disconnected or write fails.
        """
        if self._device is None:
            raise OSError("Controller not connected")

        p = self._protocol
        log.debug("Initializing %s for channels %s", p.name, channels)

        self._write(p.build_init())
        time.sleep(p.delay_init)

        for ch in channels:
            self._write(p.build_mode(ch))
            time.sleep(p.delay_mode)

        self._initialized = True
        log.info("Controller initialized (channels %s, manual mode)", channels)

    def set_fan_speed(self, speed_percent: float, channels: tuple[int, ...]) -> None:
        """Set fan speed on specified channels.

        Sends only speed commands (init/mode must have been called first).
        Raises OSError if the controller is disconnected or write fails.
        """
        if self._device is None:
            raise OSError("Controller not connected")
        if not self._initialized:
            raise OSError("Controller not initialized")

        p = self._protocol
        log.debug(
            "Setting fan speed: %.1f%% (byte value: %d)",
            speed_percent, p.speed_to_byte(speed_percent),
        )

        for ch in channels:
            self._write(p.build_speed(ch, speed_percent))
            time.sleep(p.delay_speed)
