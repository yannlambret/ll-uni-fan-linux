"""Tests for fan speed profiles, curve interpolation, and hysteresis."""

import pytest

from ll_uni_fan_linux.profile import PROFILES, SpeedController

BALANCED = PROFILES["balanced"]   # 40°C → 30%, 80°C → 100%
SILENT = PROFILES["silent"]       # 40°C → 20%, 80°C → 80%
PERF = PROFILES["performance"]    # 40°C → 50%, 80°C → 100%


# --- FanCurve interpolation ---

class TestFanCurve:
    def test_below_low_threshold(self) -> None:
        assert BALANCED.compute_speed(20.0) == 30.0

    def test_above_high_threshold(self) -> None:
        assert BALANCED.compute_speed(95.0) == 100.0

    def test_at_low_threshold(self) -> None:
        assert BALANCED.compute_speed(40.0) == 30.0

    def test_at_high_threshold(self) -> None:
        assert BALANCED.compute_speed(80.0) == 100.0

    def test_midpoint(self) -> None:
        # 60°C = midpoint → 30 + 0.5 * 70 = 65%
        assert BALANCED.compute_speed(60.0) == pytest.approx(65.0)

    def test_quarter_point(self) -> None:
        # 50°C = 25% of range → 30 + 0.25 * 70 = 47.5%
        assert BALANCED.compute_speed(50.0) == pytest.approx(47.5)

    def test_silent_profile_midpoint(self) -> None:
        # 60°C → 20 + 0.5 * 60 = 50%
        assert SILENT.compute_speed(60.0) == pytest.approx(50.0)

    def test_performance_profile_low(self) -> None:
        assert PERF.compute_speed(30.0) == 50.0


# --- SpeedController hysteresis ---

class TestSpeedController:
    def test_first_call_always_returns_speed(self) -> None:
        sc = SpeedController(BALANCED)
        assert sc.update(60.0) == pytest.approx(65.0)

    def test_within_hysteresis_returns_none(self) -> None:
        sc = SpeedController(BALANCED)
        sc.update(60.0)
        assert sc.update(61.0) is None
        assert sc.update(59.0) is None

    def test_beyond_hysteresis_returns_new_speed(self) -> None:
        sc = SpeedController(BALANCED)
        sc.update(60.0)
        result = sc.update(70.0)
        assert result is not None
        assert result == pytest.approx(82.5)

    def test_hysteresis_reference_updates_on_change(self) -> None:
        sc = SpeedController(BALANCED)
        sc.update(40.0)   # ref = 40
        sc.update(50.0)   # ref = 50 (delta=10, changes)
        # Now within ±2 of new reference (50)
        assert sc.update(51.0) is None

    def test_large_temp_delta_but_same_speed_returns_none(self) -> None:
        """Both 20°C and 30°C map to the minimum 30% → no speed change."""
        sc = SpeedController(BALANCED)
        sc.update(20.0)   # 30%
        assert sc.update(30.0) is None  # still 30%, no change

    def test_profile_change_resets_hysteresis(self) -> None:
        sc = SpeedController(BALANCED)
        sc.update(60.0)
        sc.curve = SILENT
        # After profile change, next call should always return a speed
        result = sc.update(60.0)
        assert result is not None
        assert result == pytest.approx(50.0)
