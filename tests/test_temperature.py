"""Tests for CPU temperature reading with mocked sensors."""

from collections import namedtuple
from unittest.mock import patch

from ll_uni_fan_linux.temperature import read_cpu_temperature

# psutil uses namedtuples for sensor entries
SensorEntry = namedtuple("shwtemp", ["label", "current", "high", "critical"])


class TestReadCpuTemperature:
    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_preferred_label_package(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.return_value = {  # type: ignore[attr-defined]
            "coretemp": [
                SensorEntry("Core 0", 55.0, 100.0, 100.0),
                SensorEntry("Package id 0", 58.0, 100.0, 100.0),
            ]
        }
        assert read_cpu_temperature() == 58.0

    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_preferred_label_tctl(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.return_value = {  # type: ignore[attr-defined]
            "k10temp": [SensorEntry("Tctl", 62.0, 95.0, 95.0)]
        }
        assert read_cpu_temperature() == 62.0

    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_fallback_to_max_coretemp(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.return_value = {  # type: ignore[attr-defined]
            "coretemp": [
                SensorEntry("Core 0", 50.0, 100.0, 100.0),
                SensorEntry("Core 1", 55.0, 100.0, 100.0),
            ]
        }
        assert read_cpu_temperature() == 55.0

    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_empty_sensors_returns_none(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.return_value = {}  # type: ignore[attr-defined]
        assert read_cpu_temperature() is None

    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_exception_returns_none(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.side_effect = OSError("no sensors")  # type: ignore[attr-defined]
        assert read_cpu_temperature() is None

    @patch("ll_uni_fan_linux.temperature.psutil")
    def test_last_resort_max_across_all(self, mock_psutil: object) -> None:
        mock_psutil.sensors_temperatures.return_value = {  # type: ignore[attr-defined]
            "unknown_driver": [
                SensorEntry("Sensor A", 42.0, 100.0, 100.0),
                SensorEntry("Sensor B", 47.0, 100.0, 100.0),
            ]
        }
        assert read_cpu_temperature() == 47.0
