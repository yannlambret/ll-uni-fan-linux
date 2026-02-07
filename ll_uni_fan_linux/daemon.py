"""Main daemon entry point: temperature polling and fan speed control loop."""

import logging
import signal
import sys
import time

from ll_uni_fan_linux.config import Config
from ll_uni_fan_linux.controller import Controller
from ll_uni_fan_linux.profile import PROFILES, SpeedController
from ll_uni_fan_linux.protocol import load_protocol
from ll_uni_fan_linux.temperature import read_cpu_temperature

log = logging.getLogger(__name__)

USB_RECONNECT_INTERVAL = 10.0  # seconds between reconnection attempts


class Daemon:
    """Main daemon that ties together temperature reading, speed control, and USB."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._controller = Controller(load_protocol(config.protocol))
        self._speed_ctrl = SpeedController(PROFILES[config.profile])
        self._running = True

    def _on_shutdown(self, signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        log.info("Received %s, shutting down", sig_name)
        self._running = False

    def _on_reload(self, _signum: int, _frame: object) -> None:
        log.info("Received SIGHUP, reloading configuration")
        try:
            config = Config.load([])
            self._config = config
            self._speed_ctrl.curve = PROFILES[config.profile]
            log.info("Configuration reloaded: profile=%s", config.profile)
        except (ValueError, KeyError) as e:
            log.error("Failed to reload configuration: %s", e)

    def _ensure_connected(self) -> bool:
        """Try to connect and initialize the USB controller."""
        if self._controller.connected:
            return True

        if not self._controller.find_and_open():
            log.warning(
                "USB controller not found, retrying in %.0f seconds", USB_RECONNECT_INTERVAL
            )
            return False

        try:
            self._controller.initialize(self._config.channels)
        except OSError as e:
            log.warning("Controller initialization failed: %s", e)
            self._controller.close()
            return False

        return True

    def _safe_shutdown(self) -> None:
        """Set fans to safe speed before exiting."""
        if not self._controller.connected:
            return

        try:
            if not self._controller._initialized:
                self._controller.initialize(self._config.channels)
            self._controller.set_fan_speed(self._config.safe_speed, self._config.channels)
            log.info("Fans set to safe speed (%.0f%%)", self._config.safe_speed)
        except OSError as e:
            log.warning("Failed to set safe speed on shutdown: %s", e)

        self._controller.close()

    def _wait(self, seconds: float) -> None:
        """Sleep in small increments so we can respond to signals promptly."""
        end = time.monotonic() + seconds
        while self._running and time.monotonic() < end:
            time.sleep(min(0.5, end - time.monotonic()))

    def run(self) -> None:
        """Main loop: read temperature, compute speed, send to controller."""
        log.info(
            "Starting daemon with protocol=%s, profile=%s, poll_interval=%.1fs, channels=%s",
            self._config.protocol,
            self._config.profile,
            self._config.poll_interval,
            self._config.channels,
        )

        signal.signal(signal.SIGTERM, self._on_shutdown)
        signal.signal(signal.SIGINT, self._on_shutdown)
        signal.signal(signal.SIGHUP, self._on_reload)

        while self._running:
            if not self._ensure_connected():
                self._wait(USB_RECONNECT_INTERVAL)
                continue

            temp = read_cpu_temperature()
            if temp is None:
                log.warning("Could not read CPU temperature")
                self._wait(self._config.poll_interval)
                continue

            log.debug("CPU temperature: %.1f°C", temp)

            new_speed = self._speed_ctrl.update(temp)
            if new_speed is not None:
                log.info("Temperature %.1f°C → fan speed %.0f%%", temp, new_speed)
                try:
                    self._controller.set_fan_speed(new_speed, self._config.channels)
                except OSError as e:
                    log.warning("USB write failed: %s — will attempt reconnection", e)
                    self._controller.close()
                    continue

            self._wait(self._config.poll_interval)

        self._safe_shutdown()
        log.info("Daemon stopped")


def main() -> None:
    """Entry point."""
    try:
        config = Config.load()
    except (ValueError, SystemExit) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    config.setup_logging()
    Daemon(config).run()


if __name__ == "__main__":
    main()
