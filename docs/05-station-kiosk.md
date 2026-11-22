# Line-side kiosk: screen, compute and scanner with no table space

Applies to the assembly-line stations (aluminium-profile frame, roller conveyor, overhead tool balancers and socket strip)
and to the IR test station. Software: `kiosk/` (browser kiosk) and `src/scan_forwarder/` (scanner to webhook).

## Hardware layout (per station)

| Item | What to use | Notes |
|---|---|---|
| Screen | Existing monitor with 75×75 or 100×100 VESA holes | Eye level, tilted down 10–15°, out of the overhead tool-balancer swing |
| Mount | **T-slot VESA plate or profile-mount monitor arm** on the top horizontal profile | A desk C-clamp arm is made for a flat desk edge and does not grip a profile well. Get a mount whose T-nuts match your profile slot (measure it: e.g. 40×40 with 8 mm slot vs 30×30 with 6 mm slot) |
| Compute | Raspberry Pi 4 **4 GB** (or Pi 5) in a heatsink case, on a VESA bracket behind the monitor; or a used tiny/mini PC | 2 GB is tight for Chromium with a heavy web app. Behind a monitor gets warm: use a metal heatsink case. Use the official 5.1 V / 3 A PSU on the overhead strip; cheap PSUs cause undervoltage resets |
| Storage | A30-rated (or industrial) microSD, or a USB SSD | Power cuts corrupt cheap SD cards. See "Power loss" below |
| Scanner | Fixed-mount 2D scanner in **presentation / auto-sense mode**, USB | Mount on an L-bracket on the vertical profile so the label passes 10–15° off-perpendicular to the scan window (straight-on reflects off glossy labels). Confirm it reads your symbology (1D Code128 vs DataMatrix/QR) and your label size at the mount distance |
| Network | Ethernet if the frame has a drop; else Wi-Fi | Wi-Fi near motors and the hipot tester can drop out; the forwarder queues scans to disk while offline (Option B) |

**At the IR / hipot station** keep the screen, Pi and scanner cables away from the CC2670P HV and return leads and outside
the enclosure. Power the Pi from the station's earthed supply. Nothing in this kit replaces the hardware interlock
(see `01-test-procedure-and-safety.md`).

Parts list with sellers and prices: `docs/06-bill-of-materials.csv`. Prices are from public listings (Nov 2026), not quotes.

## Getting scans into ops.leanwatts.com: pick ONE option per station

| | **A. Browser kiosk (keyboard wedge)** | **B. Background forwarder** |
|---|---|---|
| Scanner mode | USB HID keyboard, suffix Enter | USB HID keyboard (or USB-COM), suffix Enter |
| How data arrives | Scanner "types" into the focused field of the LeanWatts page | `scan-forwarder` POSTs JSON to a LeanWatts webhook/API |
| Needs from LeanWatts | A page whose scan input keeps focus | A webhook/API endpoint + token |
| Fails when | Focus moves (operator taps elsewhere, a popup, a session-expired page) and the scan is typed into nothing or the wrong field | Endpoint changes or token expires (rejected scans go to `rejected.jsonl`) |
| Offline | Scan lost | Queued on disk, sent when the network returns |

**They do not combine on the same scanner.** The forwarder grabs the scanner exclusively, so the browser never sees its
keystrokes. That is deliberate: it is what stops a scan landing in a random field.

Recommendation: **B if LeanWatts offers an API or webhook**, because a missed or misplaced serial on a moving line is
hard to notice. Use A only if the LeanWatts page has a dedicated scan screen that always re-focuses its input.

For the **IR test station**, option A already works with this repo's GUI: set `KIOSK_URL=http://127.0.0.1:8080`.
The serial field has focus on load, and Enter starts the test.

## Setup (Raspberry Pi OS with desktop, Bookworm or later)

```bash
git clone <this repo> && cd EoL-IR-testing
sudo ./kiosk/setup-pi.sh                 # Option A
sudo ./kiosk/setup-pi.sh --forwarder     # Option B (also installs the kiosk; point it at any page you like)
sudo nano /etc/eol-kiosk.env             # KIOSK_URL
sudo nano /etc/scan-forwarder.env        # Option B: SCANNER_DEVICE, SCAN_WEBHOOK_URL, SCAN_WEBHOOK_TOKEN, STATION_ID
sudo reboot
```

What it does: boot to desktop with auto-login, screen blanking off, Chromium full-screen on `KIOSK_URL` (restarted if it
closes), station software in `/opt/eol-station/venv`, and, with `--forwarder`, the `scan-forwarder` systemd service.

The browser uses a **persistent profile** (not incognito) so the LeanWatts login survives reboots. Log in once with a
keyboard, then unplug it. Ask LeanWatts for a station account whose session does not expire mid-shift.

### Scanner configuration (from its programming-barcode manual)
- Interface: USB HID keyboard (USB-COM also works with `--serial /dev/ttyACM0` in the service file).
- Keyboard language: US. Suffix: CR (Enter). No prefix.
- Mode: presentation / auto-sense. Same-code delay: about 2–3 s. The forwarder also drops repeats within `--debounce` seconds (default 3).
- Disable symbologies you don't use, so carton and supplier barcodes are not read by mistake. `SCAN_PATTERN` (regex) is a second filter.

### Forwarder payload
```json
{"serial": "LW12345678", "station_id": "LINE1-ST01", "scanned_at": "2026-11-22T10:15:03.120+00:00", "source": "hid"}
```
POST, `Content-Type: application/json`, `Authorization: Bearer $SCAN_WEBHOOK_TOKEN` if set. 2xx = delivered.
5xx, timeouts and network errors are retried with backoff (1 s up to 60 s), oldest first. Other 4xx are written to
`/var/lib/scan-forwarder/rejected.jsonl` and skipped, so one bad scan cannot block the queue.
If LeanWatts needs different field names, change `make_payload()` in `src/scan_forwarder/core.py`.

Check it: `journalctl -u scan-forwarder -f`, then scan a label. Bench test without a scanner:
`echo LW12345678 | scan-forwarder --stdin --url <endpoint> --spool /tmp/q.jsonl`.

### Power loss
The station will be switched off at the wall. The forwarder fsyncs every scan before sending, and the kiosk clears
Chromium's "didn't shut down correctly" bar. For extra SD-card safety, `raspi-config` > Performance > Overlay file
system makes the root read-only, but then the LeanWatts login and the scan queue are lost at every reboot. Only use it
if the station account can auto-login and you use option A.

## Open questions
1. How does LeanWatts take scans: a focused form field (A) or a webhook/REST API (B)? If B: URL, auth, field names.
2. How many stations, and is it one scanner per station?
3. Monitor VESA pattern (75 or 100) and weight; aluminium profile size and slot width.
4. Serial label format and symbology (gives `SCAN_PATTERN` and the scanner settings).
5. Ethernet or Wi-Fi at the line?
