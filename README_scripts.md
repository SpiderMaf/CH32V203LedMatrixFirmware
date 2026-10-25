# CH32V203 LED Matrix — Firmware Patch Scripts

Two dependency-free Python 3 tools for a **specific 65,536-byte CHV firmware layout**. They are not universal CH32V203 firmware patchers.

## 1. Skip the heart mode

```bash
python3 patch_modes.py CHV_dump_original.bin CHV_no_heart.bin --omit heart
```

`--omit none` copies the input unchanged. The heart patch changes **four bytes** at offsets `0x1F1E` and `0x1F25`–`0x1F27`, redirecting the normal mode 2 → mode 0 transition to mode 1. It **does not** change the saved startup mode, so a previously saved heart state may still be selected on power-up.

Only `heart` and `none` are supported; other modes have not been safely patched or tested.

## 2. Replace the four letter bitmaps

```bash
python3 patch_letters.py CHV_no_heart.bin CHV_no_heart_SUBS.bin --text SUBS
```

The script changes exactly four 240-byte, 15×16 bitmaps (one byte per LED, 0 or 1). It leaves animation logic and mode changes alone. Built-in character designs: **L O V E S U B**. The `SUBS` output is identical to the previously prepared `CHV_skip_heart_SUBS.bin` when run against the heart-patched original.

To use another character, provide a JSON object mapping each new character to **16 strings of 15 characters** using `#` for on and `.` for off:

```json
{
  "X": [
    "...............",
    "##...........##",
    ".##.........##.",
    "..##.......##..",
    "...##.....##...",
    "....##...##....",
    ".....##.##.....",
    "......###......",
    "......###......",
    ".....##.##.....",
    "....##...##....",
    "...##.....##...",
    "..##.......##..",
    ".##.........##.",
    "##...........##",
    "..............."
  ]
}
```

Save as `glyphs.json`, then:

```bash
python3 patch_letters.py CHV_no_heart.bin CHV_no_heart_XUBS.bin --text XUBS --glyphs glyphs.json
```

Bitmap offsets in **display order**: `0x4380`, `0x4290`, `0x41A0`, `0x40B0`. These correspond to the original `L`, `O`, `V`, `E` positions.

## Check and flash

The scripts refuse to overwrite the input and require a 65,536-byte image. The mode script also checks expected machine-code bytes before modifying them.

Keep your original dumps safe. For this specific board and `wlink` setup, the **hardware-tested** flash command for the heart patch was:

```bash
wlink flash --chip CH32V20X --erase -a 0x08000000 CHV_no_heart_SUBS.bin
```

**Warning:** `--erase` may erase stored settings and firmware. The heart patch was tested on the physical device; the new lettering appearance may still need checking. Always verify a readback and retain an untouched original firmware backup. Never flash these patches to a different firmware revision without verifying the instruction signatures and bitmap layout.
