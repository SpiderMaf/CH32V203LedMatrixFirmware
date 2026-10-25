# Hacking a CH32V203 LED Matrix – Removing the Heart and Changing the Firmware

*A little reverse engineering, some RISC-V assembly, and a surprising amount of arguing with a flashing utility.*

## The project

SpiderMaf recently picked up one of those rather clever little LED matrix gadgets. It's a small PCB featuring a dense array of green LEDs, a rechargeable battery, an accelerometer and a USB-C connector.

At its heart (pun unfortunately intended) is a **WCH CH32V203 RISC-V microcontroller**.

The original firmware has three animation modes:

- **LOVE** – Displays the letters L, O, V and E individually.
- **Beating heart** – A pulsing heart animation.
- **Water simulation** – A rather impressive fluid effect that reacts to tilting the board.

Shaking the gadget switches between animations.

The water simulation is particularly good, so SpiderMaf wanted to keep it. The heart animation, however, was a prime candidate for retirement.

The goal was to extract the original firmware, understand enough of it to make some changes, and eventually replace the lettering with something a little more interesting.

Ideally without turning the gadget into a very small, very green paperweight.

## 1. Getting access to the microcontroller

The first challenge was finding a way to communicate with the CH32V203.

Connecting the board to a Mac via USB-C powered it and charged the battery, but didn't expose a useful USB programming interface. Holding the onboard button during connection didn't help either.

Fortunately, the PCB had some exposed programming pads, including connections labelled `DIO`, `CLK` and `GND`. These were suitable candidates for the WCH two-wire debug interface.

A **WCH-Link programmer** was connected to the relevant pads, providing direct access to the microcontroller.

On macOS, I used the open-source Rust utility [wlink](https://github.com/ch32-rs/wlink).

The programmer initially needed switching into RISC-V mode:

```bash
wlink mode-switch --rv
```

Then I checked that it was visible:

```bash
wlink list
```

With the programmer connected and communicating, it was time to see whether the original firmware could be recovered.

## 2. Extracting the firmware

The CH32V203's application flash begins at `0x08000000`.

I used `wlink` to read the full 64 KB flash region:

```bash
wlink dump --chip CH32V20X -o CHV_dump_original.bin 0x08000000 65536
```

This produced a **65,536-byte binary firmware image**.

I then performed a second extraction and compared the files:

```bash
cmp CHV_dump_original.bin CHV_dump_second.bin
```

No output from `cmp` meant the two files were identical.

That was encouraging. At least we had a repeatable readout and a backup of the original firmware before experimenting.

**Important:** Keep an untouched copy of the original firmware. Preferably two. This is not the point in the project where we want to discover the backup was called `final_final_really_final.bin` and accidentally overwritten.

## 3. Investigating the firmware

The next step was reverse-engineering the binary.

Rather than attempting to rewrite the entire program, I used ChatGPT to help analyse the RISC-V instructions and identify specific routines.

The firmware contains executable code, animation data, character bitmaps and a region containing repeated filler bytes.

We concentrated on three areas:

1. The LOVE character bitmaps.
2. The animation selection and timing logic.
3. The mode-switching state machine.

### Finding the LOVE bitmaps

One of the first useful discoveries was that the letters are stored as straightforward monochrome bitmap data.

Each character occupies **240 bytes**, corresponding to a 15 × 16 LED matrix. Each pixel is represented by a byte:

- `0x00` – LED off
- `0x01` – LED on

The original character locations were identified as:

| Letter | Binary offset | Size |
|---|---|---|
| E | `0x40B0` | 240 bytes |
| V | `0x41A0` | 240 bytes |
| O | `0x4290` | 240 bytes |
| L | `0x4380` | 240 bytes |

Interestingly, the bitmaps appear in reverse display order in the firmware: E, V, O, L. The program selects them in the correct order when displaying LOVE.

This was a particularly useful discovery because changing the text wouldn't necessarily require rewriting the LED driving code. We could simply replace the bitmap data.

### Finding the lettering routines

Disassembly identified the following relevant code locations:

| Offset | Purpose |
|---|---|
| `0x0552` | Clear the LED display |
| `0x0576` | Render bitmap data |
| `0x05B8` | Select the current LOVE character |
| `0x0600` | Letter animation and timing |
| `0x0632` | Four-character limit |

The character index runs from 0 to 3. At `0x0632`, the firmware loads the value `3` as the maximum index. When the index exceeds that value, it wraps back to zero.

This is interesting for future modifications because increasing the number of letters should be possible, although the bitmap selection routine would also need extending. Simply changing the maximum from 3 to 8 wouldn't be enough to display nine different letters.

## 4. Finding the animation state machine

The next challenge was removing the beating-heart animation without disturbing the water simulation.

The firmware maintains an animation mode variable in RAM at `0x20000084`.

The three states were identified as:

| Mode | Animation |
|---|---|
| 0 | Heart / particle animation |
| 1 | Water simulation |
| 2 | LOVE lettering |

The mode-switching routine was located at offset `0x1E3A`.

Originally, the firmware cycles through all three modes: `0 → 1 → 2 → 0`.

We also identified the corresponding initialisation routines:

| Offset | Purpose |
|---|---|
| `0x1CEC` | Heart / particle initialisation |
| `0x064A` | Water simulation initialisation |
| `0x05EA` | LOVE animation initialisation |

The main animation dispatch also references the mode variable, with the lettering animation called from around `0x2888`.

The mode-switch routine was the important part for this first experiment. Rather than deleting the heart animation's code, we could simply stop the normal mode cycle from selecting it.

## 5. Bypassing the heart animation

The original mode-switching sequence was:

```text
Heart → Water → LOVE → Heart
```

The desired sequence was:

```text
Water → LOVE → Water → LOVE
```

Two small changes were made to the existing machine code:

| Offset | Original behaviour | Modified behaviour |
|---|---|---|
| `0x1F1C` | Set mode to 0 | Set mode to 1 |
| `0x1F24` | Call heart initialiser | Call water initialiser |

The resulting firmware differed from the original in only **four bytes**. The heart animation code itself was left in place.

This was deliberate: the less code we changed, the less opportunity there was to break something unrelated.

A new 64 KB binary was generated, preserving the original water simulation and LOVE animation.

### The flashing adventure

This part took longer than expected.

Initially, `wlink` reported that flashing had completed successfully:

```text
Fastprogram done
Flash done
Now reset...
```

But the gadget behaved exactly as before. Dumping the firmware again revealed that the original instructions were still present.

So despite the reassuring messages, our modified code hadn't actually made it onto the chip.

The solution was to explicitly specify both the erase operation and the flash base address.

The command that successfully worked on my CH32V203 was:

```bash
wlink flash --chip CH32V20X --erase -a 0x08000000 CHV_skip_heart_test.bin
```

**Warning:** `--erase` can erase existing firmware and stored flash data. Make sure you have a verified backup and a recovery method before using it.

After flashing with this command, the board finally behaved as intended.

**The beating heart was gone from the normal animation cycle!**

The gadget continued to switch between the LOVE lettering and the water simulation.

That's the first successful modification of the original firmware, tested on the actual hardware.

## 6. Replacing LOVE with SUBS

With the mode-switch patch working, the next experiment was to change the lettering without touching the display routines.

Since LOVE uses four 15 × 16 bitmaps, another four-letter sequence could fit into exactly the same space.

I chose **S → U → B → S**.

New bitmap patterns were generated for those four characters, retaining the original 240-byte-per-character format.

The replacement data was written to the same locations:

| Original | Replacement | Offset |
|---|---|---|
| L | S | `0x4380` |
| O | U | `0x4290` |
| V | B | `0x41A0` |
| E | S | `0x40B0` |

The existing animation timing and character-selection code were left unchanged.

This produced a second experimental firmware image combining the heart-removal modification with the SUBS bitmap replacements.

At the time of writing, the heart-removal modification has been tested successfully on the hardware. The SUBS lettering patch has been generated, but its appearance on the physical LED matrix still needs validating.

## 7. What next? A bigger font and SPIDERMAF

The obvious next step is to extend the lettering beyond four characters.

The existing firmware already provides almost everything needed:

- A working bitmap renderer.
- Known 15 × 16 character dimensions.
- A character index and animation timer.
- Identified character-selection logic.

The limitation is that the current code selects only four fixed bitmap addresses.

To support more letters, we'd need to add additional bitmap data and modify the selection routine to address a larger character table.

For example, displaying **SPIDERMAF** would require nine character positions, with nine distinct letter designs.

At 240 bytes per bitmap, nine characters would occupy **2,160 bytes**.

An even more interesting approach would be to add a reusable alphabet, allowing arbitrary messages rather than hard-coded four-letter sequences.

That would require more extensive reverse engineering, plus careful identification of genuinely unused flash space.

But it should be possible to preserve the original water simulation rather than rebuilding everything from scratch.

And that's really the point of this project. The existing firmware already does something rather clever. The aim is to extend it, not throw it away.

## Tools used

- WCH CH32V203 microcontroller
- WCH-Link debug/programming adapter
- macOS Terminal
- [wlink](https://github.com/ch32-rs/wlink) 0.1.3
- `cmp` and `xxd`
- RISC-V disassembly and binary analysis
- Python for firmware bitmap and binary modifications
- ChatGPT for analysis and patch development

## Final thoughts

What started as a cheap little LED gadget has turned into a rather entertaining firmware reverse-engineering project.

We've successfully extracted its original firmware, identified the character bitmaps, traced the animation state machine, and made a four-byte modification that removes an entire animation from the normal sequence.

All without the original source code.

There have been a few false starts, particularly around flashing, but that's part of the fun.

Next up: getting the gadget to display something more interesting than LOVE.

Possibly SPIDERMAF.

Because apparently even a tiny green LED matrix isn't safe from channel branding.

— **SpiderMaf** 🕷️
