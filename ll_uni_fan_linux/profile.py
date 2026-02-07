"""Fan speed profiles with linear interpolation and hysteresis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FanCurve:
    """A linear fan curve defined by two temperature/speed anchor points."""

    temp_low: float   # Lower temperature threshold (°C)
    speed_low: float  # Fan speed at low temp (0-100%)
    temp_high: float  # Upper temperature threshold (°C)
    speed_high: float # Fan speed at high temp (0-100%)

    def compute_speed(self, temperature: float) -> float:
        """Compute fan speed for a given temperature using linear interpolation."""
        if temperature <= self.temp_low:
            return self.speed_low
        if temperature >= self.temp_high:
            return self.speed_high

        # Linear interpolation
        ratio = (temperature - self.temp_low) / (self.temp_high - self.temp_low)
        return self.speed_low + ratio * (self.speed_high - self.speed_low)


PROFILES: dict[str, FanCurve] = {
    "silent": FanCurve(temp_low=40.0, speed_low=20.0, temp_high=80.0, speed_high=80.0),
    "balanced": FanCurve(temp_low=40.0, speed_low=30.0, temp_high=80.0, speed_high=100.0),
    "performance": FanCurve(temp_low=40.0, speed_low=50.0, temp_high=80.0, speed_high=100.0),
}

# Hysteresis threshold: the temperature must change by at least this many degrees
# from the point where the last speed was set before a new speed is applied.
# This prevents rapid oscillations when the temperature hovers around a point.
HYSTERESIS_DEGREES = 2.0


class SpeedController:
    """Computes fan speed from temperature with hysteresis.

    Hysteresis works by remembering the temperature at which the last speed change
    was applied. A new speed is only computed if the current temperature deviates
    from that reference by more than HYSTERESIS_DEGREES.
    """

    def __init__(self, curve: FanCurve) -> None:
        self._curve = curve
        self._last_speed: float | None = None
        self._reference_temp: float | None = None

    @property
    def curve(self) -> FanCurve:
        return self._curve

    @curve.setter
    def curve(self, value: FanCurve) -> None:
        self._curve = value
        # Reset hysteresis state on profile change
        self._last_speed = None
        self._reference_temp = None

    def update(self, temperature: float) -> float | None:
        """Compute the target fan speed for the given temperature.

        Returns the new speed percentage if a change should be applied,
        or None if the current speed should be maintained (hysteresis).
        """
        # Always apply on first call
        if self._last_speed is None or self._reference_temp is None:
            speed = self._curve.compute_speed(temperature)
            self._last_speed = speed
            self._reference_temp = temperature
            return speed

        # Check hysteresis: has temp moved enough from the reference point?
        delta = abs(temperature - self._reference_temp)
        if delta < HYSTERESIS_DEGREES:
            return None

        new_speed = self._curve.compute_speed(temperature)

        # Only apply if the speed actually changes meaningfully (>= 1%)
        if abs(new_speed - self._last_speed) < 1.0:
            return None

        self._last_speed = new_speed
        self._reference_temp = temperature
        return new_speed
