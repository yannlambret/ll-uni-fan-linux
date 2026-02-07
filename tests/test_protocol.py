"""Tests for protocol definitions and command building."""

import pytest

from ll_uni_fan_linux.protocol import available_protocols, load_protocol


class TestLoadProtocol:
    def test_load_sl_inf(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.name == "Lian-Li UNI FAN SL-INF"
        assert proto.vendor_id == 0x0CF2
        assert proto.product_id == 0xA102

    def test_load_sl_v1(self) -> None:
        proto = load_protocol("lian-li-sl-v1")
        assert proto.name == "Lian-Li UNI FAN SL V1"
        assert proto.product_id == 0xA100

    def test_load_al_v1(self) -> None:
        proto = load_protocol("lian-li-al-v1")
        assert proto.name == "Lian-Li UNI FAN AL V1"
        assert proto.product_id == 0xA101

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown protocol 'nonexistent'"):
            load_protocol("nonexistent")

    def test_available_protocols(self) -> None:
        keys = available_protocols()
        assert "lian-li-sl-inf" in keys
        assert "lian-li-sl-v1" in keys
        assert "lian-li-al-v1" in keys


class TestSpeedToByte:
    @pytest.mark.parametrize("pct, expected", [
        (0, 9),
        (30, 36),
        (50, 54),
        (100, 100),
    ])
    def test_sl_inf_known_values(self, pct: float, expected: int) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.speed_to_byte(pct) == expected

    def test_clamped_below_zero(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.speed_to_byte(-10) == proto.speed_to_byte(0)

    def test_clamped_above_100(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.speed_to_byte(150) == proto.speed_to_byte(100)

    def test_monotonically_increasing(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        values = [proto.speed_to_byte(p) for p in range(101)]
        assert values == sorted(values)

    def test_sl_v1_different_range(self) -> None:
        proto = load_protocol("lian-li-sl-v1")
        # SL v1: byte = int((800 + 11 * speed) / 19)
        assert proto.speed_to_byte(0) == 42
        assert proto.speed_to_byte(100) == 100


class TestBuildCommands:
    def test_build_init(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.build_init() == [0xE0, 0x10, 0x61, 0, 0, 0, 0]

    def test_build_mode_channel_0(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.build_mode(0) == [0xE0, 0x10, 0x62, 0x10]

    def test_build_mode_channel_2(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        assert proto.build_mode(2) == [0xE0, 0x10, 0x62, 0x40]

    def test_build_speed(self) -> None:
        proto = load_protocol("lian-li-sl-inf")
        cmd = proto.build_speed(1, 50.0)
        assert cmd == [0xE0, 0x21, 0x00, 54]

    def test_al_v1_uses_different_init_byte(self) -> None:
        proto = load_protocol("lian-li-al-v1")
        assert proto.build_init() == [0xE0, 0x10, 0x41, 0, 0, 0, 0]

    def test_sl_v1_uses_different_mode_byte(self) -> None:
        proto = load_protocol("lian-li-sl-v1")
        assert proto.build_mode(0) == [0xE0, 0x10, 0x31, 0x10]
