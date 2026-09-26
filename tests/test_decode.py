"""Decoding tests against recorded captures. No device needed."""
import json
import struct
from pathlib import Path

import pytest

from powermate import (CMD_PULSE_MODE, PID, PULSE_DIVIDE, PULSE_MULTIPLY,
                       PULSE_NORMAL, VID, Event, parse_report, pulse_mode_args)

CAPTURES = Path(__file__).resolve().parent.parent / "captures"


def load(name):
    return [json.loads(l)["raw"] for l in open(CAPTURES / name)]


@pytest.mark.parametrize("raw,event", [
    ([0, 0, 0], Event(False, 0)),
    ([1, 0, 0], Event(True, 0)),
    ([0, 1, 0], Event(False, 1)),
    ([0, 0xFF, 0], Event(False, -1)),
    ([0, 19, 0], Event(False, 19)),
    ([0, 0xED, 0], Event(False, -19)),
    ([0, 0x7F, 0], Event(False, 127)),
    ([0, 0x81, 0], Event(False, -127)),
    ([1, 10, 0], Event(True, 10)),
])
def test_parse_report(raw, event):
    assert parse_report(raw) == event


@pytest.mark.parametrize("raw", [[], [0, 0], [0, 0, 0, 0, 0, 0]])
def test_parse_report_rejects_other_lengths(raw):
    with pytest.raises(ValueError):
        parse_report(raw)


def test_session1_matches_recorded_analysis():
    reports = load("input_session1.jsonl")
    assert len(reports) == 331
    assert all(len(r) == 3 and r[2] == 0 for r in reports)
    events = [parse_report(r) for r in reports]
    deltas = [e.delta for e in events]
    assert sum(e.pressed for e in events) == 3
    assert max(deltas) == 19 and min(deltas) == -19


def test_session2_matches_recorded_analysis():
    events = [parse_report(r) for r in load("input_session2.jsonl")]
    assert len(events) == 133
    assert sum(e.delta for e in events) == 11
    assert sum(e.pressed for e in events) == 13
    # Turning while held is reported.
    assert any(e.pressed and e.delta for e in events)


def test_report_timestamps_increase():
    for name in ("input_session1.jsonl", "input_session2.jsonl"):
        t = [json.loads(l)["t"] for l in open(CAPTURES / name)]
        assert t == sorted(t)


@pytest.mark.parametrize("table,op,arg,expected", [
    (0, PULSE_NORMAL, 0, (0x0004, 0x0001)),
    (0, PULSE_DIVIDE, 255, (0x0004, 0xFF00)),
    (0, PULSE_MULTIPLY, 255, (0x0004, 0xFF02)),
    (1, PULSE_NORMAL, 0, (0x0104, 0x0001)),
    (2, PULSE_NORMAL, 0, (0x0204, 0x0001)),
])
def test_pulse_mode_args(table, op, arg, expected):
    assert pulse_mode_args(table, op, arg) == expected
    assert expected[0] & 0xFF == CMD_PULSE_MODE


@pytest.mark.parametrize("table,op,arg", [(0, 3, 0), (256, 1, 0), (0, 1, -1),
                                          (0, 0, 256)])
def test_pulse_mode_args_rejects_bad_values(table, op, arg):
    with pytest.raises(ValueError):
        pulse_mode_args(table, op, arg)


def test_device_descriptor_capture():
    d = (CAPTURES / "device_descriptor.bin").read_bytes()
    (length, dtype, bcd_usb, cls, sub, proto, mps0, vid, pid, bcd_dev,
     i_man, i_prod, i_ser, n_conf) = struct.unpack("<BBHBBBBHHHBBBB", d)
    assert (length, dtype, bcd_usb) == (18, 1, 0x0100)
    assert (cls, sub, proto, mps0) == (0, 0, 0, 8)
    assert (vid, pid, bcd_dev) == (VID, PID, 0x0109)
    assert (i_man, i_prod, i_ser, n_conf) == (1, 2, 0, 1)


def test_config_descriptor_capture():
    c = (CAPTURES / "config_descriptor.bin").read_bytes()
    assert len(c) == struct.unpack_from("<H", c, 2)[0] == 34
    # Walk the bundle by bLength / bDescriptorType.
    parts, i = {}, 0
    while i < len(c):
        parts.setdefault(c[i + 1], c[i:i + c[i]])
        i += c[i]
    assert set(parts) == {0x02, 0x04, 0x21, 0x05}
    iface = parts[0x04]
    assert (iface[4], iface[5], iface[6], iface[7]) == (1, 3, 1, 2)  # 1 EP, HID boot mouse
    hid = parts[0x21]
    assert struct.unpack_from("<HBBBH", hid, 2) == (0x0100, 0, 1, 0x22, 50)
    ep = parts[0x05]
    assert ep[2] == 0x81 and ep[3] == 0x03  # EP1 IN, interrupt
    assert struct.unpack_from("<H", ep, 4)[0] == 3 and ep[6] == 10


def test_report_descriptor_capture_is_3_byte_mouse():
    r = (CAPTURES / "hid_report_descriptor.bin").read_bytes()
    assert len(r) == 50
    assert r[:4] == bytes.fromhex("05010902")  # Generic Desktop, Mouse
    # No output (0x91) or feature (0xB1) main items, and no report IDs (0x85).
    items, i = [], 0
    while i < len(r):
        size = (0, 1, 2, 4)[r[i] & 0x03]
        items.append(r[i] & 0xFC)
        i += 1 + size
    assert 0x90 not in items and 0xB0 not in items and 0x84 not in items
    assert items.count(0x80) == 3  # three Input items: buttons, padding, X/Y
