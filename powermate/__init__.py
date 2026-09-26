"""Griffin PowerMate (USB 077d:0410) access for macOS.

Input comes through hidapi, because macOS's HID driver owns the interface.
LED commands are vendor control transfers sent through libusb, which macOS
still allows to reach the interface while the HID driver holds it.
"""
from dataclasses import dataclass

VID = 0x077D
PID = 0x0410
LIBUSB_PATH = "/opt/homebrew/lib/libusb-1.0.dylib"

# Vendor request: bmRequestType 0x41, bRequest 0x01, wValue = command.
REQTYPE_VENDOR_INTERFACE = 0x41
REQUEST = 0x01
CMD_STATIC_BRIGHTNESS = 0x01
CMD_PULSE_ASLEEP = 0x02
CMD_PULSE_AWAKE = 0x03
CMD_PULSE_MODE = 0x04

PULSE_DIVIDE, PULSE_NORMAL, PULSE_MULTIPLY = 0, 1, 2


@dataclass(frozen=True)
class Event:
    pressed: bool
    delta: int  # clockwise positive


def parse_report(raw):
    """Decode one 3-byte input report: buttons, rotation (X), unused (Y)."""
    if len(raw) != 3:
        raise ValueError(f"expected 3-byte report, got {len(raw)}")
    delta = raw[1] - 256 if raw[1] > 127 else raw[1]
    return Event(pressed=bool(raw[0] & 0x01), delta=delta)


def pulse_mode_args(table, op, arg):
    """Return (wValue, wIndex) for the pulse mode command."""
    if op not in (PULSE_DIVIDE, PULSE_NORMAL, PULSE_MULTIPLY):
        raise ValueError("op must be 0 (divide), 1 (normal) or 2 (multiply)")
    for name, v in (("table", table), ("arg", arg)):
        if not 0 <= v <= 255:
            raise ValueError(f"{name} must be 0-255")
    return (table << 8) | CMD_PULSE_MODE, (arg << 8) | op


class PowerMate:
    def __init__(self):
        import usb.backend.libusb1
        import usb.core

        backend = usb.backend.libusb1.get_backend(
            find_library=lambda x: LIBUSB_PATH)
        self.usb = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        if self.usb is None:
            raise RuntimeError("PowerMate not found")
        self._hid = None

    @property
    def hid(self):
        # Opened on first use: hidapi's open is exclusive on macOS, and the
        # LED commands only need libusb, so they must not take the device.
        if self._hid is None:
            import hid
            self._hid = hid.device()
            self._hid.open(VID, PID)
        return self._hid

    def close(self):
        if self._hid is not None:
            self._hid.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _command(self, value, index):
        self.usb.ctrl_transfer(REQTYPE_VENDOR_INTERFACE, REQUEST,
                               value, index, None)

    def brightness(self, level):
        if not 0 <= level <= 255:
            raise ValueError("level must be 0-255")
        self._command(CMD_STATIC_BRIGHTNESS, level)

    def pulse(self, table=0, op=PULSE_NORMAL, arg=0):
        self._command(*pulse_mode_args(table, op, arg))
        self._command(CMD_PULSE_AWAKE, 1)

    def pulse_off(self, level=0):
        self._command(CMD_PULSE_AWAKE, 0)
        self.brightness(level)

    def pulse_asleep(self, on):
        self._command(CMD_PULSE_ASLEEP, 1 if on else 0)

    def read(self, timeout_ms=None):
        """Return the next Event, or None if timeout_ms passes first."""
        raw = self.hid.read(64, timeout_ms) if timeout_ms else self.hid.read(64)
        return parse_report(raw) if raw else None

    def report_descriptor(self):
        return bytes(self.hid.get_report_descriptor())

    def device_descriptor(self):
        return bytes(self.usb.ctrl_transfer(0x80, 0x06, 0x0100, 0, 18))

    def config_descriptor(self):
        return bytes(self.usb.ctrl_transfer(0x80, 0x06, 0x0200, 0, 255))
