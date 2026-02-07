"""Tests for the generic USB HID controller with mocked device."""

from unittest.mock import MagicMock, patch

import pytest

from ll_uni_fan_linux.controller import Controller
from ll_uni_fan_linux.protocol import load_protocol

PROTO = load_protocol("lian-li-sl-inf")


def _make_connected_controller() -> tuple[Controller, MagicMock]:
    """Create a Controller with a mocked HID device, already initialized."""
    mock_dev = MagicMock()
    ctrl = Controller(PROTO)
    ctrl._device = mock_dev
    ctrl._initialized = True
    return ctrl, mock_dev


class TestControllerInitialize:
    @patch("ll_uni_fan_linux.controller.time.sleep")
    def test_initialize_sends_init_and_mode(self, mock_sleep: MagicMock) -> None:
        mock_dev = MagicMock()
        ctrl = Controller(PROTO)
        ctrl._device = mock_dev

        ctrl.initialize((0, 1, 2))
        writes = [c.args[0] for c in mock_dev.write.call_args_list]

        assert writes[0] == bytes(PROTO.build_init())
        assert writes[1] == bytes(PROTO.build_mode(0))
        assert writes[2] == bytes(PROTO.build_mode(1))
        assert writes[3] == bytes(PROTO.build_mode(2))
        assert mock_dev.write.call_count == 4
        assert ctrl._initialized is True

    def test_initialize_not_connected_raises(self) -> None:
        ctrl = Controller(PROTO)
        with pytest.raises(OSError, match="not connected"):
            ctrl.initialize((0,))


class TestControllerSetFanSpeed:
    @patch("ll_uni_fan_linux.controller.time.sleep")
    def test_speed_commands_only(self, mock_sleep: MagicMock) -> None:
        ctrl, mock_dev = _make_connected_controller()
        channels = (0, 1, 2)
        ctrl.set_fan_speed(50.0, channels)

        writes = [c.args[0] for c in mock_dev.write.call_args_list]
        for i, ch in enumerate(channels):
            assert writes[i] == bytes(PROTO.build_speed(ch, 50.0))

        assert mock_dev.write.call_count == len(channels)

    def test_not_connected_raises(self) -> None:
        ctrl = Controller(PROTO)
        with pytest.raises(OSError, match="not connected"):
            ctrl.set_fan_speed(50.0, (0,))

    def test_not_initialized_raises(self) -> None:
        ctrl = Controller(PROTO)
        ctrl._device = MagicMock()
        ctrl._initialized = False
        with pytest.raises(OSError, match="not initialized"):
            ctrl.set_fan_speed(50.0, (0,))


class TestControllerConnection:
    @patch("ll_uni_fan_linux.controller.hid")
    def test_find_and_open_no_device(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = []
        ctrl = Controller(PROTO)
        assert ctrl.find_and_open() is False
        assert ctrl.connected is False

    @patch("ll_uni_fan_linux.controller.hid")
    def test_find_and_open_success(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = [
            {"path": b"/dev/hidraw0", "serial_number": "ABC123"}
        ]
        mock_hid.device.return_value = MagicMock()

        ctrl = Controller(PROTO)
        assert ctrl.find_and_open() is True
        assert ctrl.connected is True
        assert ctrl._initialized is False
        mock_hid.enumerate.assert_called_once_with(PROTO.vendor_id, PROTO.product_id)

    def test_close_resets_state(self) -> None:
        ctrl, mock_dev = _make_connected_controller()
        ctrl._device_path = b"/dev/hidraw0"

        ctrl.close()
        assert ctrl.connected is False
        assert ctrl._initialized is False
        mock_dev.close.assert_called_once()

    def test_close_tolerates_os_error(self) -> None:
        ctrl, mock_dev = _make_connected_controller()
        mock_dev.close.side_effect = OSError("USB gone")

        ctrl.close()  # should not raise
        assert ctrl.connected is False
