"""Record raw PowerMate input reports with timestamps.

Usage: .venv/bin/python tools/capture_input.py SECONDS OUTFILE.jsonl
Each line: {"t": seconds since start, "raw": [bytes]}. Also flashes the LED
at start and end so the capture window is visible on the device.
"""
import json
import sys
import time

import hid
import usb.backend.libusb1
import usb.core

VID, PID = 0x077D, 0x0410


def led(level):
    be = usb.backend.libusb1.get_backend(
        find_library=lambda x: "/opt/homebrew/lib/libusb-1.0.dylib")
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=be)
    dev.ctrl_transfer(0x41, 0x01, 0x0001, level, None)


def main():
    secs, out = float(sys.argv[1]), sys.argv[2]
    h = hid.device()
    h.open(VID, PID)
    h.set_nonblocking(1)
    led(255)
    start = time.monotonic()
    n = 0
    with open(out, "w") as f:
        while (t := time.monotonic() - start) < secs:
            r = h.read(64)
            if r:
                n += 1
                f.write(json.dumps({"t": round(t, 4), "raw": r}) + "\n")
            else:
                time.sleep(0.001)
    led(0)
    h.close()
    print(f"{n} reports in {secs:.0f}s -> {out}")


if __name__ == "__main__":
    main()
