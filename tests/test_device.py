"""Hardware checks. Skipped when no PowerMate is plugged in.

These cover what can be checked without a person: descriptors match the
captures, and the device accepts or refuses control requests as documented.
Whether the LED visibly changes is covered by tools/interactive_test.py.
The LED is left off afterwards.
"""
from pathlib import Path

import pytest
import usb.core

from powermate import (CMD_PULSE_AWAKE, CMD_STATIC_BRIGHTNESS, REQUEST,
                       PowerMate)

CAPTURES = Path(__file__).resolve().parent.parent / "captures"


@pytest.fixture(scope="module")
def pm():
    try:
        dev = PowerMate()
    except RuntimeError:
        pytest.skip("PowerMate not plugged in")
    yield dev
    dev.pulse_off(0)
    dev.close()


def test_device_descriptor_matches_capture(pm):
    assert pm.device_descriptor() == (CAPTURES / "device_descriptor.bin").read_bytes()


def test_config_descriptor_matches_capture(pm):
    assert pm.config_descriptor() == (CAPTURES / "config_descriptor.bin").read_bytes()


def test_report_descriptor_matches_capture(pm):
    try:
        desc = pm.report_descriptor()
    except OSError:
        pytest.skip("HID side is open in another process (exclusive open)")
    assert desc == (CAPTURES / "hid_report_descriptor.bin").read_bytes()


def test_strings(pm):
    get = lambda i: usb.util.get_string(pm.usb, i)
    assert get(1) == "Griffin Technology, Inc."
    assert get(2) == "Griffin PowerMate"
    assert get(4) == "Volume Control"
    assert get(5) == "Endpoint 1"


@pytest.mark.parametrize("level", [0, 1, 128, 255])
def test_brightness_accepted(pm, level):
    pm.brightness(level)


@pytest.mark.parametrize("level", [-1, 256])
def test_brightness_range_checked(pm, level):
    with pytest.raises(ValueError):
        pm.brightness(level)


@pytest.mark.parametrize("table,op,arg", [(0, 1, 0), (0, 0, 255), (0, 2, 255),
                                          (1, 1, 0), (2, 1, 0)])
def test_pulse_accepted(pm, table, op, arg):
    pm.pulse(table, op, arg)
    pm.pulse_off(0)


def test_device_recipient_vendor_request_stalls(pm):
    # Only the interface recipient (0x41) works; the device stalls 0x40.
    with pytest.raises(usb.core.USBError) as e:
        pm.usb.ctrl_transfer(0x40, REQUEST, CMD_STATIC_BRIGHTNESS, 0, None)
    assert e.value.errno == 32


def test_interface_standard_request_denied_on_macos(pm):
    # macOS's HID driver owns the interface, so libusb cannot read the
    # HID report descriptor directly.
    with pytest.raises(usb.core.USBError) as e:
        pm.usb.ctrl_transfer(0x81, 0x06, 0x2200, 0, 64)
    assert e.value.errno == 13


def test_idle_device_sends_nothing(pm):
    try:
        assert pm.read(timeout_ms=300) is None
    except OSError:
        pytest.skip("HID side is open in another process (exclusive open)")


def test_pulse_awake_off_accepted(pm):
    pm._command(CMD_PULSE_AWAKE, 0)
