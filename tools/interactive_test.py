"""Guided hardware test: knob input is checked automatically, LED by asking.

Usage: .venv/bin/python tools/interactive_test.py
Run it in a real terminal. Results are printed and saved to
captures/interactive_<timestamp>.json.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from powermate import PowerMate  # noqa: E402

WINDOW = 6.0  # seconds to perform each knob action


def collect(pm, seconds):
    events, end = [], time.monotonic() + seconds
    while time.monotonic() < end:
        e = pm.read(timeout_ms=50)
        if e:
            events.append(e)
    return events


def presses(events):
    """Count up-to-down transitions of the button."""
    return sum(1 for a, b in zip([None] + events, events)
               if b.pressed and (a is None or not a.pressed))


def knob_step(pm, prompt, check, describe):
    input(f"\n{prompt}\nPress Enter, then do it within {WINDOW:.0f} seconds...")
    while pm.read(timeout_ms=1):  # drop anything queued while waiting
        pass
    events = collect(pm, WINDOW)
    ok = check(events)
    print(f"  {'PASS' if ok else 'FAIL'}: {describe(events)}")
    return ok, describe(events)


def ask(question):
    while True:
        a = input(f"  {question} [y/n] ").strip().lower()
        if a in ("y", "n"):
            return a == "y"


def led_step(pm, prompt, action, question):
    input(f"\n{prompt}\nPress Enter and watch the LED...")
    action()
    ok = ask(question)
    print(f"  {'PASS' if ok else 'FAIL'}")
    return ok, question


def main():
    results = {}
    total = lambda ev: sum(e.delta for e in ev)
    with PowerMate() as pm:
        pm.pulse_off(0)
        results["clockwise"] = knob_step(
            pm, "Turn the knob CLOCKWISE about half a turn.",
            lambda ev: total(ev) > 20,
            lambda ev: f"{len(ev)} reports, total {total(ev):+d} (want > +20)")
        results["counter_clockwise"] = knob_step(
            pm, "Turn the knob COUNTER-CLOCKWISE about half a turn.",
            lambda ev: total(ev) < -20,
            lambda ev: f"{len(ev)} reports, total {total(ev):+d} (want < -20)")
        results["press"] = knob_step(
            pm, "PRESS and release the knob 3 times, without turning it.",
            lambda ev: presses(ev) == 3,
            lambda ev: f"{presses(ev)} presses (want 3)")
        results["press_and_turn"] = knob_step(
            pm, "HOLD the knob down and turn it, then release.",
            lambda ev: any(e.pressed and e.delta for e in ev),
            lambda ev: f"{sum(1 for e in ev if e.pressed and e.delta)} reports "
                       "with button held and rotation (want at least 1)")

        results["led_full"] = led_step(
            pm, "LED full brightness.", lambda: pm.brightness(255),
            "Is the LED on at full brightness?")
        results["led_dim"] = led_step(
            pm, "LED dim.", lambda: pm.brightness(8),
            "Is the LED on but clearly dimmer?")
        results["led_off"] = led_step(
            pm, "LED off.", lambda: pm.brightness(0),
            "Is the LED off?")
        results["pulse"] = led_step(
            pm, "LED pulsing.", lambda: pm.pulse(),
            "Is the LED pulsing (fading up and down)?")
        results["pulse_off"] = led_step(
            pm, "Pulse stopped.", lambda: pm.pulse_off(0),
            "Has the LED stopped pulsing and gone off?")

    passed = sum(ok for ok, _ in results.values())
    print(f"\n{passed}/{len(results)} passed")
    out = (Path(__file__).resolve().parent.parent / "captures"
           / time.strftime("interactive_%Y%m%d_%H%M%S.json"))
    out.write_text(json.dumps(
        {k: {"pass": ok, "detail": d} for k, (ok, d) in results.items()},
        indent=1) + "\n")
    print(f"saved {out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
