# Griffin PowerMate: USB protocol reference

Everything here was observed on one unit, on macOS (Darwin 25.6), on
2026-09-25. Raw bytes are in `captures/`. Where something comes from the
Linux kernel driver (`drivers/input/misc/powermate.c`) and was not confirmed
on this unit, it says so.

## Summary

- The PowerMate presents itself as a **standard 3-button boot mouse**.
  Rotation is the X axis, the knob press is button 1, Y is always 0.
- It has **no HID output or feature reports**. The LED is controlled only
  by **vendor control requests** on endpoint 0.
- The input report carries **no LED state**, so the LED cannot be read back.
- About **100 counts per revolution**, clockwise positive.

## Identity

| Field | Value |
| --- | --- |
| Vendor ID | `0x077D` (Griffin Technology, Inc.) |
| Product ID | `0x0410` (Griffin PowerMate) |
| Device release (bcdDevice) | `0x0109` (1.09) |
| USB version (bcdUSB) | 1.00 |
| Speed | Low speed (1.5 Mbit/s) |
| Power | Bus powered, 100 mA |
| Serial number | None (iSerialNumber = 0) |

## Descriptors

### Device descriptor (`captures/device_descriptor.bin`)

`12 01 00 01 00 00 00 08 7d 07 10 04 09 01 01 02 00 01`

| Offset | Field | Value |
| --- | --- | --- |
| 0 | bLength | 18 |
| 1 | bDescriptorType | 1 (Device) |
| 2 | bcdUSB | 0x0100 |
| 4 | bDeviceClass / SubClass / Protocol | 0 / 0 / 0 (defined per interface) |
| 7 | bMaxPacketSize0 | 8 |
| 8 | idVendor | 0x077D |
| 10 | idProduct | 0x0410 |
| 12 | bcdDevice | 0x0109 |
| 14 | iManufacturer | 1: "Griffin Technology, Inc." |
| 15 | iProduct | 2: "Griffin PowerMate" |
| 16 | iSerialNumber | 0 (none) |
| 17 | bNumConfigurations | 1 |

### Configuration bundle (`captures/config_descriptor.bin`, 34 bytes)

`09 02 22 00 01 01 04 80 32` `09 04 00 00 01 03 01 02 05`
`09 21 00 01 00 01 22 32 00` `07 05 81 03 03 00 0a`

| Descriptor | Fields |
| --- | --- |
| Configuration | wTotalLength 34, 1 interface, bConfigurationValue 1, iConfiguration 4 ("Volume Control"), bmAttributes 0x80 (bus powered), bMaxPower 0x32 (100 mA) |
| Interface 0 | alt 0, 1 endpoint, class 3 (HID), subclass 1 (boot), protocol 2 (mouse), iInterface 5 ("Endpoint 1") |
| HID | bcdHID 1.00, country code 0, 1 class descriptor: type 0x22 (report), length 50 |
| Endpoint | 0x81 (EP1 IN), interrupt, wMaxPacketSize 3, bInterval 10 ms |

There is no OUT endpoint.

### String descriptors (`captures/string_descriptors.json`)

| Index | Content |
| --- | --- |
| 0 | Language IDs: 0x0409 (English, US) |
| 1 | "Griffin Technology, Inc." |
| 2 | "Griffin PowerMate" |
| 3 | Exists but is **empty**. Nothing refers to it. |
| 4 | "Volume Control" |
| 5 | "Endpoint 1" |
| 6 and up | Stall |

### HID report descriptor (`captures/hid_report_descriptor.bin`, 50 bytes)

| Bytes | Item |
| --- | --- |
| `05 01` | Usage Page (Generic Desktop) |
| `09 02` | Usage (Mouse) |
| `a1 01` | Collection (Application) |
| `09 01` | . Usage (Pointer) |
| `a1 00` | . Collection (Physical) |
| `05 09` | . . Usage Page (Button) |
| `19 01` `29 03` | . . Usage Minimum 1, Usage Maximum 3 |
| `15 00` `25 01` | . . Logical Minimum 0, Logical Maximum 1 |
| `95 03` `75 01` | . . Report Count 3, Report Size 1 |
| `81 02` | . . Input (Data, Variable, Absolute): 3 buttons |
| `95 01` `75 05` | . . Report Count 1, Report Size 5 |
| `81 01` | . . Input (Constant): 5 bits of padding |
| `05 01` | . . Usage Page (Generic Desktop) |
| `09 30` `09 31` | . . Usage X, Usage Y |
| `15 81` `25 7f` | . . Logical Minimum -127, Logical Maximum 127 |
| `75 08` `95 02` | . . Report Size 8, Report Count 2 |
| `81 06` | . . Input (Data, Variable, Relative): X, Y |
| `c0` `c0` | End Collection, End Collection |

No report IDs, no output reports, no feature reports.

## Input report

Three bytes on EP1 IN, sent only when something changes. Nothing arrives
while the knob is idle.

| Byte | HID meaning | PowerMate meaning |
| --- | --- | --- |
| 0 | Buttons (bits 0-2) | Bit 0 = knob pressed. Bits 1-7 were never seen set. |
| 1 | X, signed 8-bit relative | Rotation since the last report. Clockwise positive. |
| 2 | Y, signed 8-bit relative | Always 0. |

Observed behaviour (`captures/input_session1.jsonl`, `input_session2.jsonl`):

- Slow turning sends runs of +1 or -1. The knob is smooth, with no detents.
- Movement accumulates between reports: fast hand spins gave up to +/-19
  in a single report.
- One hand-marked clockwise revolution summed to +103, so about 100 counts
  per revolution. An exact figure is issue #10.
- Press and release each produce one report with delta 0.
- Turning while pressed is reported normally, with byte 0 = 1 and the
  rotation in byte 1.
- The shortest gap between reports was about 31 ms, although bInterval
  asks for 10 ms. Whether the device or macOS sets that limit is issue #10.

**Linux driver difference.** The Linux driver describes a 6-byte report
whose bytes 3 and 4 carry LED brightness and pulse status. This unit
(bcdDevice 1.09) sends only the 3-byte mouse report above, so none of that
applies here.

## LED control

All LED commands are control transfers on endpoint 0 with no data stage:

| Field | Value |
| --- | --- |
| bmRequestType | `0x41` (host to device, vendor, recipient interface) |
| bRequest | `0x01` |
| wValue | command in the low byte (table in the high byte for pulse mode) |
| wIndex | argument |
| wLength | 0 |

The same request with recipient **device** (`0x40`) is stalled.

| Command | wValue | wIndex | Status |
| --- | --- | --- | --- |
| Static brightness | `0x0001` | level 0-255 | Confirmed |
| Pulse while asleep | `0x0002` | 1 on, 0 off | From Linux. Default behaviour confirmed (see below); the command itself not tested |
| Pulse while awake | `0x0003` | 1 on, 0 off | Confirmed on/off |
| Pulse mode | `(table << 8) \| 0x04` | `(arg << 8) \| op` | Accepted, effect not measured |

### Static brightness

0 is off and 255 is full. At power-up the LED comes on at brightness 128.
In a sweep of 0, 1, 2, 4, 8 ... 255 the LED was
visible from 1 and every step was brighter than the one before. The exact
brightness curve was not measured.

### Power-up and sleep defaults

Reported by the user on 2026-09-26:

- LED settings **do not survive** unplugging. After replugging, the LED
  comes back at static brightness 128.
- With nothing sent beyond the tests in this document (and never the
  `0x0002` command), the LED **pulses while the Mac is asleep**. So pulsing
  during host sleep is the device's default behaviour, presumably triggered
  by USB suspend.

### Pulsing

To pulse: send pulse mode, then pulse while awake = 1. To go back to a
steady LED: send pulse while awake = 0, then static brightness.

Pulse mode parameters, following the Linux driver:

| op | Meaning | arg |
| --- | --- | --- |
| 0 | Divide: slower than normal | larger arg is slower |
| 1 | Normal speed | 0 |
| 2 | Multiply: faster than normal | larger arg is faster |

`table` selects one of three pulse waveforms (0, 1, 2).

The device accepted every combination tried (table 0, 1, 2; op 0, 1, 2 with
arg 0 or 255) and the LED pulsed, but no one could tell the settings apart
by eye. What each speed and table actually does is issue #11.

## macOS access notes

- macOS's HID driver owns interface 0 and treats the knob as a mouse:
  turning it **moves the pointer** (confirmed). While a program holds the
  exclusive hidapi open (for example `python -m powermate watch`), the
  pointer stops moving and knob presses stop acting as mouse clicks (both
  confirmed by the user).
- **Input:** use hidapi. It opens the device **exclusively**: a second
  process trying to open it gets `OSError: open failed`.
- **LED:** use libusb (pyusb with the Homebrew `libusb-1.0.dylib`). Vendor
  requests to the interface go through even while the HID driver holds it.
- **Descriptors:** standard requests to the *device* recipient work through
  libusb. Standard requests to the *interface* recipient (such as reading
  the HID report descriptor) are refused with "access denied". hidapi's
  `get_report_descriptor()` works instead.
- No sudo and no Input Monitoring prompt were needed for any of this.
- A blocking `hid.read()` does not return to Python on Ctrl-C. Read with a
  timeout.

## Not tested

- Sending the pulse-while-asleep command (`0x0002`), e.g. whether 0 stops
  the sleep pulse.
- Whether LED settings survive host sleep and wake.
- Command values other than 0x01-0x04, and GET requests (issue #6).
- Any operating system other than macOS.
