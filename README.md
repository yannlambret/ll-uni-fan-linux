# ll-uni-fan-linux

A Linux daemon that automatically controls Lian-Li UNI FAN speed based on CPU temperature, communicating with the official USB controller via HID.

## Features

- Temperature-based fan speed control with linear interpolation
- Three built-in profiles: silent, balanced, performance
- Hysteresis to prevent rapid speed oscillations
- Automatic USB controller reconnection on disconnect
- Safe fan speed on daemon shutdown (default: 90%)
- Runtime configuration reload via SIGHUP
- Hardware-agnostic design with YAML-based protocol definitions

## Supported Hardware

Protocol definitions are stored in [`protocols.yaml`](ll_uni_fan_linux/protocols.yaml). The active protocol is selected via the `PROTOCOL` configuration parameter.

| Key              | Model                    | Status          |
|------------------|--------------------------|-----------------|
| `lian-li-sl-inf` | Lian-Li UNI FAN SL-INF   | Fully Supported |
| `lian-li-sl-v1`  | Lian-Li UNI FAN SL V1    | Fully Supported |
| `lian-li-al-v1`  | Lian-Li UNI FAN AL V1    | Untested        |

Adding a new controller model only requires a new entry in `protocols.yaml`.

## Prerequisites

- Python 3.10+

## Installation

```bash
# Install the daemon (from a local clone)
sudo pipx install .

# Or directly from the repository
sudo pipx install git+https://github.com/yannlambret/ll-uni-fan-linux.git
```

### udev Rule

The daemon needs access to the USB HID device. Install the provided udev rule to grant access without running as root:

```bash
sudo cp system/99-lian-li.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### systemd Service

```bash
# Create a dedicated system user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin -G plugdev fanctl

# Install the service and default configuration
sudo cp system/ll-uni-fan-linux.service /etc/systemd/system/
sudo cp system/ll-uni-fan-linux.default /etc/default/ll-uni-fan-linux

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now ll-uni-fan-linux
```

## Configuration

The daemon reads its configuration from three sources, in order of priority:

1. CLI arguments (highest)
2. Environment variables (set by systemd `EnvironmentFile`)
3. `/etc/default/ll-uni-fan-linux`
4. Built-in defaults (lowest)

### Configuration File

Edit `/etc/default/ll-uni-fan-linux`:

```bash
# Fan controller protocol (see protocols.yaml for available keys)
PROTOCOL=lian-li-sl-inf

# Fan profile: silent, balanced, performance
PROFILE=balanced

# Temperature polling interval in seconds
POLL_INTERVAL=3

# Active fan channels (comma-separated, 0-3)
CHANNELS=0,1,2,3

# Fan speed set on daemon shutdown (0-100%)
SAFE_SPEED=90

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Enable debug mode (overrides LOG_LEVEL to DEBUG)
DEBUG=false
```

Reload at runtime without restarting the service:

```bash
systemctl kill -s HUP ll-uni-fan-linux
```

### CLI Arguments

```bash
ll-uni-fan-linux --profile performance --debug
ll-uni-fan-linux --protocol lian-li-sl-v1 --channels 0,1 --poll-interval 5
```

## Fan Profiles

| Profile       | 40°C | 80°C | Description              |
|---------------|------|------|--------------------------|
| `silent`      | 20%  | 80%  | Prioritizes low noise    |
| `balanced`    | 30%  | 100% | Default, balanced        |
| `performance` | 50%  | 100% | Maximum cooling          |

Fan speed is linearly interpolated between the two temperature anchor points.
Below 40°C, the minimum speed is held; above 80°C, the maximum speed is held.
A 2°C hysteresis prevents rapid oscillations near temperature thresholds.

## Troubleshooting

### USB controller not detected

Check that the controller is visible on the USB bus:

```bash
lsusb | grep 0cf2
```

The daemon automatically retries the connection every 10 seconds.

### Permission denied on HID device

Install the udev rule (see [Installation](#udev-rule)) and make sure the `fanctl` user belongs to the `plugdev` group.

### No temperature readings

Ensure your CPU thermal driver is loaded. The daemon reads temperatures via `psutil`, which uses the kernel's hwmon interface (`/sys/class/hwmon/`):

```bash
python3 -c "import psutil; print(psutil.sensors_temperatures())"
```

## Development

```bash
# Set up the virtual environment
poetry install

# Run the daemon locally
poetry run ll-uni-fan-linux --debug --profile performance

# Run tests
poetry run pytest

# Lint
poetry run ruff check .
```

## Acknowledgments

USB HID protocol reverse-engineered from [uni-sync](https://github.com/EightB1ts/uni-sync).
