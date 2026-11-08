[简体中文](官方导出pxt64指导.md) | English

# Exporting a `.pxt64` Game Cartridge from the Official MakeCode Arcade IDE — Illustrated Guide

> Applies to: arcade v4.1.27 / Microsoft MakeCode v13.1.24 (the official online
> version at the time of writing). All you need is a browser — nothing to install.

## What this document solves

The official MakeCode Arcade online IDE (<https://arcade.makecode.com>) is
**hardware-oriented by default**: clicking **Download** produces a `.uf2`
firmware image to flash onto a handheld board (F4 / R2, etc.).

But the core also ships a **VM (virtual machine) target** — select it and the
very same **Download** button stops producing firmware and instead produces a
`.pxt64` **bytecode cartridge** you can run directly. That target is currently
classified as "experimental hardware", hidden by default, and has to be
enabled by hand.

Follow the screenshots below, step by step.

---

## Step 1: Open the About dialog

Go to the <https://arcade.makecode.com> home page and click the **gear icon in
the top-right corner** (⚙ Settings), then choose **About...** from the menu.

![Step 1: About in the top-right gear menu](2026-11-04%2020%2040%2030.png)

The menu also has Language, Theme, Reset and friends — none of them need
touching.

## Step 2: Enter the Experiments page

In the **About** dialog, check the two version numbers (at the time of writing
`arcade version: 4.1.27` and `Microsoft MakeCode version: 13.1.24`), then click
the purple **Experiments** button (**not** the green Ok — that just closes the
dialog).

![Step 2: the Experiments button in the About dialog](2026-11-04%2020%2040%2043.png)

## Step 3: Enable Experimental Hardware (i.e. VM)

The experiments page opens with a yellow warning: "WARNING: EXPERIMENTAL
FEATURES AHEAD!". Find the card in the middle whose preview image says **VM** —
**Experimental Hardware** (described as "Enable support for hardware marked
'experimental' in the ...") — and click the **Disabled** tag in its top-right
corner to flip it to **Enabled** (the tag turns green).

![Step 3: the experiments list, with Experimental Hardware (VM) boxed in red](2026-11-04%2020%2040%2055.png)

## Step 4: Leave the page so the editor reloads

Once enabled, a banner appears at the bottom of the page:

> **Experiments changed** — The editor will reload when leaving this page.

There is no confirm button to hunt for: just click **← Go back** in the
top-left corner. The editor reloads itself once and picks up the VM target.

![Step 4: Experimental Hardware now Enabled, with the Experiments changed banner at the bottom](2026-11-04%2020%2041%2004.png)

> The switch is stored in your browser locally (localStorage / cookie) and is
> **persistent** for that browser — you won't need to redo this. Switching
> browsers, clearing site data, or using a private window means repeating
> steps 1–4.

## Step 5: Choose VM as the target hardware

Open (or create) a project and enter the editor. Click the **small `...` button
next to Download in the bottom-left corner** and choose **Choose Hardware**
from the popup menu.

![Step 5: Choose Hardware in the ... menu next to Download](2026-11-04%2020%2041%2050.png)

The hardware list shows three cards: **F4** (STM32F4xx board), **R2**
(Raspberry Pi RP2040 board), and **VM** (its preview simply says "VM") — pick
**VM**.

![Step 6: the hardware dialog, with VM boxed in red](2026-11-04%2020%2042%2008.png)

## Step 6: Click Download to get the .pxt64

Back in the editor with VM selected, click **Download** in the bottom-left
corner:

![Step 6: the Download and ... buttons in the editor's bottom-left corner](2026-11-04%2020%2048%2030.png)

The browser pops up a normal download prompt. The file name follows the pattern
`arcade-<project name>.pxt64` (for example
`arcade-Magnate-by-Octodemon.pxt64`). Choose **Save** and you have the
**`.pxt64` game cartridge** produced by the official compiler.

![Step 7: the browser downloading arcade-xxx.pxt64](2026-11-04%2020%2045%2048.png)

> If you have previously selected a hardware target, **Download as File** in
> the same menu does the same job — it forces the output to be downloaded as a
> file (instead of trying to reach a USB device). Under the VM target the two
> are equivalent.

---

## Quick reference

| Step | Action |
|---|---|
| 1 | Top-right ⚙ → **About...** |
| 2 | About dialog → **Experiments** |
| 3 | Click the **Experimental Hardware** card: Disabled → **Enabled** |
| 4 | **← Go back**; the editor reloads itself |
| 5 | Editor bottom-left **...** → **Choose Hardware** → **VM** |
| 6 | Click **Download** → the browser saves `arcade-<project>.pxt64` |

## FAQ

**Q: Why does my Download give me a `.uf2`?**
The hardware target is still F4/R2 — switch to VM as in step 5. The VM card only
appears in the list after steps 1–4 are done.

**Q: Do I have to redo this on another browser or computer?**
Yes. Both the experiment toggle and the hardware selection live in browser
storage; they don't follow your account.

**Q: What is the exported `.pxt64` good for?**
- It can be loaded and run directly by any player/core that supports pxt64
  (such as the makecode-arcade-libretro core);
- It can be compared for consistency against local toolchain output (this
  repository's `tools/pxt64diff.py` diffs it section by section — cartconv
  output has been verified **byte-identical** to official same-version
  toolchain output).

**Q: Is enabling the experiment risky?**
The VM target is labelled experimental and Microsoft doesn't promise
stability; but it only changes *what kind of artifact* gets produced — your
project source is untouched. To turn it off, do the same thing in reverse
(click the card back to Disabled).
