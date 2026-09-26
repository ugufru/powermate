"""Command line: python -m powermate {info,watch,led,pulse,off}."""
import argparse
import sys

from . import PowerMate


def main(argv=None):
    p = argparse.ArgumentParser(prog="powermate")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info", help="print descriptors")
    sub.add_parser("watch", help="print rotation and button events")
    led = sub.add_parser("led", help="set static brightness")
    led.add_argument("level", type=int)
    pulse = sub.add_parser("pulse", help="pulse the LED")
    pulse.add_argument("--table", type=int, default=0)
    pulse.add_argument("--op", type=int, default=1,
                       help="0 divide (slower), 1 normal, 2 multiply (faster)")
    pulse.add_argument("--arg", type=int, default=0)
    sub.add_parser("off", help="stop pulsing and turn the LED off")
    a = p.parse_args(argv)

    with PowerMate() as pm:
        if a.cmd == "info":
            print("device:", pm.device_descriptor().hex(" "))
            print("config:", pm.config_descriptor().hex(" "))
            print("report:", pm.report_descriptor().hex(" "))
        elif a.cmd == "watch":
            total = 0
            try:
                while True:
                    # Short timeouts keep Ctrl-C responsive; a blocking
                    # hid read does not return to Python on SIGINT.
                    e = pm.read(timeout_ms=100)
                    if e is None:
                        continue
                    total += e.delta
                    print(f"delta {e.delta:+4d}  total {total:+6d}  "
                          f"{'PRESSED' if e.pressed else 'up'}", flush=True)
            except KeyboardInterrupt:
                pass
        elif a.cmd == "led":
            pm.brightness(a.level)
        elif a.cmd == "pulse":
            pm.pulse(a.table, a.op, a.arg)
        elif a.cmd == "off":
            pm.pulse_off(0)


if __name__ == "__main__":
    sys.exit(main())
