"""CPU temperature reading via psutil."""

import logging

import psutil

log = logging.getLogger(__name__)

# Preferred sensor labels in priority order
_PREFERRED_LABELS = ("Package id 0", "Tctl", "Tdie", "CPU")

# Known CPU thermal driver names
_CPU_DRIVERS = ("coretemp", "k10temp", "zenpower")


def read_cpu_temperature() -> float | None:
    """Read the current CPU temperature in degrees Celsius.

    Returns the package/die temperature if available, otherwise the max core temperature.
    Returns None if no temperature source is available.
    """
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError) as e:
        log.debug("psutil.sensors_temperatures() failed: %s", e)
        return None

    if not temps:
        return None

    # Look for preferred labels across all sensor groups
    for label in _PREFERRED_LABELS:
        for entries in temps.values():
            for entry in entries:
                if entry.label == label and entry.current > 0:
                    return entry.current

    # Fallback: highest reading from known CPU thermal drivers
    for name in _CPU_DRIVERS:
        if name in temps:
            readings = [e.current for e in temps[name] if e.current > 0]
            if readings:
                return max(readings)

    # Last resort: max across all sensors
    all_readings = [
        e.current for entries in temps.values() for e in entries if e.current > 0
    ]
    return max(all_readings) if all_readings else None
