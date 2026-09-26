# powermate

Discovering, testing and documenting the USB interface of the Griffin
PowerMate (USB `077d:0410`) on macOS.

- Protocol reference: [docs/USB.md](docs/USB.md)
- Raw descriptor and input captures: `captures/`
- Issues and roadmap: `issues.jsonl`, `roadmap.jsonl`, browsable in
  `issues.html` (rebuild with `make issues`)

## Setup

Needs Homebrew's libusb (`brew install libusb`).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Command line

```sh
.venv/bin/python -m powermate info                # descriptors as hex
.venv/bin/python -m powermate watch               # live rotation and button events
.venv/bin/python -m powermate led 128             # static brightness, 0-255
.venv/bin/python -m powermate pulse --op 1        # pulse (see docs for table/op/arg)
.venv/bin/python -m powermate off                 # stop pulsing, LED off
```

Only one process can read the knob at a time: hidapi opens it exclusively,
which also stops the knob moving the macOS pointer while it is open.
`led`, `pulse` and `off` only use libusb, so they work while `watch` runs.
`info` reads the report descriptor through hidapi, so it does not.

`tools/capture_input.py SECONDS OUT.jsonl` records raw input reports with
timestamps.

## Tests

```sh
.venv/bin/pytest                              # offline decoding tests + hardware checks
.venv/bin/python tools/interactive_test.py    # guided: you turn/press, and confirm the LED
```

`tests/test_decode.py` replays the recorded captures and needs no device.
`tests/test_device.py` checks descriptors and control requests against the
real device and skips when it is unplugged. Leave the knob alone while it
runs: one test expects the idle device to send nothing.

The interactive test saves its results to `captures/interactive_*.json`.
Pressing the knob is also a mouse click on macOS, so park the pointer
somewhere harmless first.
