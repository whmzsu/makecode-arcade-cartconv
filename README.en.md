English | [简体中文](README.md)

# cartconv — MakeCode Arcade Cartridge Converter

Converts MakeCode Arcade `.png` cartridges into `.pxt64` bytecode images that
[makecode-arcade-libretro](https://github.com/whmzsu/makecode-arcade-libretro)
(the MakeCode Arcade core for RetroArch) can run directly.

For players it ships as a **portable, install-free package**: unzip it, drop a
`.png` onto `cartconv.exe` — no Node.js, npm or Python required. See this
repo's Releases for the portable package.

## Quick Start

**Portable package (recommended)**: download
`makecode-cartconv-<ver>-windows-x64.zip` from Releases, unzip, and drop
`.png` files on it (single / multi-select / a whole folder all work).

**From source** (any platform, Node.js ≥ 16):

```bash
npm install          # inside vm-build/ — installs the pxt toolchain (locked versions)
node cartconv.js game.png
node cartconv.js carts/ -o out/     # batch
```

Put the resulting `.pxt64` on the handheld and load it in RetroArch.

## Alternative: no download — export via the official online IDE

The portable package is ~80MB. If you only need to convert a cartridge or two,
you can skip installing anything entirely — the official online IDE has the
`.pxt64` export switch built in, and the whole flow runs in the browser:

1. Open <https://arcade.makecode.com> and **drag the `.png` cartridge onto the
   page** (or use **Import** on the home page);
2. Gear ⚙ in the top-right → **About...** → click the purple **Experiments**
   button;
3. Flip the **Experimental Hardware** card (the one whose preview says **VM**)
   from `Disabled` to **Enabled**, then click **← Go back** (the editor reloads
   automatically);
4. In the editor's bottom-left, the **`...` next to Download** →
   **Choose Hardware** → pick **VM**;
5. Click **Download** — the browser downloads `arcade-<project>.pxt64`.

A step-by-step illustrated guide lives in
[`MakeCode Arcade 如何官方导出pxt64/官方导出pxt64指导.en.md`](MakeCode%20Arcade%20如何官方导出pxt64/官方导出pxt64指导.en.md)
([中文版](MakeCode%20Arcade%20如何官方导出pxt64/官方导出pxt64指导.md)).

**Both paths produce the same bytes**: for the same cartridge, the official
online toolchain (`arcade 4.1.27 / pxt 13.1.24` at the time of writing) and
this tool's bundled toolchain (`4.2.1 / 13.2.1`) produce **byte-identical**
`.pxt64` files — verified on four cartridges (ping, jumpy-platformer,
community-falling-duck, strawberry-slam; the last one with 6 GitHub
extensions), down to section count and SRCM trailer length.

Trade-offs:

| | Official online IDE | This tool |
|---|---|---|
| Install | None — just open a web page | ~80MB portable download |
| Batch conversion | One cartridge at a time, by hand | Drop a folder, or command line |
| Offline | No | Yes (`--no-net`) |
| On failure | Raw compiler error | Pre-flight check with plain-language causes and fixes |
| Community extensions | Browser fetches from GitHub | Bundled codeload / API fallback patches |

In one line: **for the occasional single cartridge, the official IDE is
easier; for batch jobs, offline use, or extension-download trouble, use this
tool.**

## Why conversion is needed

A `.png` cartridge contains only **project source code** (`meta` + `source` —
true for all 21 real cartridges tested), not compiled output. To become VM
bytecode the core can execute, it must go through the pxt compiler
(`pxt build --hwvariant vm`). That's where this tool's weight comes from —
node + pxt are unavoidable.

## Supported range: 21 real cartridges verified (but don't expect 100%)

A full regression run in November 2026 covered 21 cartridges; the corpus
lives in `png_examples/` of the
[makecode-arcade-libretro](https://github.com/whmzsu/makecode-arcade-libretro)
repository:

- **4 official examples** (ping / jumpy-platformer / falling-duck /
  cube-land) — native `.png` cartridges downloaded from the official site,
  untouched;
- **17 real community projects** — project source fetched from official
  share links, then re-packed into official-format `.png` by this repo's
  `tools/make_cart_png.py` (cover image = a frame captured from the core
  actually running the game), to cover newer editor features and lots of
  community extensions.

| Dimension | Result |
|---|---|
| Conversion | **21 / 21 succeeded**, 0 failures, 0 skipped, ~603 s total |
| Codec round-trip | The 17 re-packed samples convert back to `.pxt64` **byte-identical (sha256)** to the pre-packing original (lossless png codec) |
| Runnability | Outputs loaded into the libretro core for 600 frames: **19 normal** (two anomalies below, neither is the converter's fault) |
| Coverage | bpp=1/2, blocks & TS editors, Chinese source code, binary-asset projects |

**8 of them depend on GitHub community extensions** (both `gh:` and
`github:` spellings), up to 9 extensions on one cartridge, 22 distinct
version references in total — all downloaded on the fly and compiled
successfully while online.

The 17 community projects: blocky-boss-battle, bunny-hop, caterpillar,
cave-explorer, falling-duck, galgamulti, hot-air-balloon, jewel-raider,
kickoff, mouse-adventure, pigeon-deliverance, save-the-forest,
secure-the-river, space-destroyer, stack-the-goats, strawberry-slam,
tictactwo.

### Two known anomalies (neither is the converter's fault)

| Cartridge | Symptom | Diagnosis |
|---|---|---|
| mouse-adventure | Screen static with no input; smoke test flags `static` | **False positive**. Frame capture confirms a normal level scene (brick walls + mouse); with key presses the character moves through 21 distinct frames — the game simply doesn't animate without input |
| strawberry-slam | VM panic 980 (~5.1 s in, `PANIC_CAST_FROM_NULL`, method call on null), input-independent, fixed timing | **Likely a bug in the game itself**: its source has `game.runtime()+5000` countdown logic. Same category as the castle black screen — not introduced by the conversion chain |

To reproduce these: the smoke test must point at the newest DLL under
`core/dist/<target>/`. The old 0.2.15 build in the core repo root takes the
host down with it on panic (`0xc0000005`), which gets misread as a crash;
from 0.3.1 on, the host survives panics and the verdict is `panic`.

Beyond the verified cartridges there are no samples, hence no guarantees.
Known limitations fall into four classes; the tool detects each and explains
why:

| Situation | Tool behavior | Notes |
|---|---|---|
| Depends on community extension `gh:user/repo` | Downloads & compiles if GitHub is reachable; blocks before compile otherwise | See below |
| Extension not available locally | Verified after `install`; reports which one is missing | Official extensions work offline, third-party ones don't |
| Source contains binary assets | Written back verbatim, warn and continue | See below |
| Cartridge newer than the compiler | Warns but compiles anyway | Bundled pxt-arcade is 4.2.1 |

### Community extensions & networking (since v1.2.0)

When a cartridge uses community extensions (both `"gh:user/repo"` keys and
`"pkg": "github:user/repo#tag"` values are recognized), cartconv first probes
GitHub connectivity (codeload.github.com as the main channel +
api.github.com as fallback, 6 s timeout):

- **Reachable** → proceeds; `pxt install` downloads the extensions from
  GitHub and compiles. Download failures (missing repo, network hiccups) are
  reported as download problems — never disguised as something else;
- **Unreachable** → blocked before compile with an explanation of what's
  missing, instead of an uninformative pxt error;
- `--no-net` forces offline handling (skips the probe).

The bundled toolchain is patched on the extension download path: when
raw.githubusercontent.com is unreachable it falls back to codeload
whole-repo snapshots, then to per-file api.github.com contents API.
`testdata/net-ghdep.png` is a sample cartridge declaring a real community
extension (converts fine online; blocked as missing-extension offline).

### How binary assets are handled (since v1.2.0)

Newer MakeCode stores user-uploaded images and sounds as standalone binary
files in the project (`assets/xxx.png` etc.). These ride inside the
cartridge as latin1 byte-mapped strings; cartconv writes them back into the
build project verbatim (byte-exact) before compiling — no longer blocked.

The boundary to understand: **the local pxt compiler only consumes text
resources like `.ts`/`.jres`**; standalone binary asset files are inert to
it. So:

- Source referencing only editor-drawn graphics (stored in `*.g.jres`) →
  compiles normally; the binary files just sit in the project;
- Source referencing assets that must be compiled from binary files (e.g. an
  uploaded PNG sprite never converted to jres) → compiler error or missing
  graphics at runtime. The pre-flight check statically verifies that
  references like `assets.image\`name\`` exist in the project's `.jres`, and
  warns on mismatches as a debugging lead.

### Direction of version compatibility

First, what `meta.targetVersions` means: it records the toolchain version
**at the moment the cartridge was packed**. It says nothing about file age
and is not the version of the editor in front of you.

| Corpus | `meta.targetVersions` | Where the number comes from |
|---|---|---|
| 4 official examples | `target 1.3.44 / pxt 6.8.33` | Written when Microsoft packed these examples in **Feb 2021** (pxt-arcade 1.3.44 published 2021-02-05). The files are the ones the official site still serves today — Microsoft just never re-packed them |
| 17 community re-packed samples | `target 4.2.1 / pxt 13.2.1` | Written by `tools/make_cart_png.py` at re-pack time from the **local toolchain**, not by the official editor |
| (reference) current official online editor | `target 4.1.27 / pxt 13.1.24` | stable4.1 branch, Oct 2026; this tool's `4.2.1 / 13.2.1` is actually newer |

The real compatibility conclusion: **the whole span from `pxt 6.8.33` to
`13.2.1` works** — a 2021 cartridge goes through a compiler four years
newer, so old APIs were never removed; same-generation is trivial. The
reverse isn't guaranteed: if a cartridge uses APIs newer than 4.2.1,
compilation fails and the pre-flight check emits a version warning as a
lead.

Also note: the 17 re-packed samples carry the local toolchain's version
stamp by construction, so their byte-identical round-trip is a **closed-loop
self-test** (proves the codec is lossless) — not two independent sources
corroborating each other. The independent cross-check is the other
experiment: the same cartridge compiled by the official same-version
toolchain (4.1.27/13.1.24) and by this tool's toolchain produces identical
bytes (see the section above).

## Repository layout

```
cartconv.js          main program (arg parsing, batching, progress, compiler invocation)
cartdec.js           .png cartridge decoder (PNG → bitstream → LZMA → project JSON)
cartenc.js           cartridge encoder (testing only, not shipped)
precheck.js          pre-compile check (extensions / versions / binary assets / asset refs)
launcher.c           Windows drag-and-drop entry (zig cc → cartconv.exe)
fakebin/docker.cmd   docker stub (the pxt build tries to call docker)
keep_modules.txt     dependency whitelist (measured, see below)
prune_modules.py     prunes an existing tree by whitelist (packaging now copies positively; kept for verification)
package_cartconv.sh  builds the portable package
package.json         version number (read by the packaging script)
vm-build/            pxt toolchain dependency manifest (package.json + lockfile; node_modules not committed)
tools/png2pxt64.py   legacy conversion script (29 s/cart, kept as cartconv's reference implementation)
tools/extract_png_meta.py  .png cartridge format parsing (pure Python; byte-equivalent to cartdec.js)
tools/pxt64diff.py   section-level .pxt64 diff (section type histogram / OpCodeMap name-table diff)
tools/make_cart_png.py  project dir → official-format .png cartridge (builds regression corpus / round-trip checks)
tools/fetch_shared.py   official share id → project source → .pxt64 (bulk-harvest real games)
examples/            verification sample
testdata/            failure samples (regression for pre-flight blocking paths)
MakeCode Arcade 如何官方导出pxt64/  illustrated guide + screenshots for exporting .pxt64 from the official IDE
```

## How test samples are made

`cartenc.js` is the inverse of `cartdec.js`: project object → `.png`
cartridge. The bitstream algorithm is line-for-line from pxt's
`Util.encodeBlobAsync`; the only difference is the PNG container, written
with zlib.

Its purpose is manufacturing failure samples — real cartridges can't cover
those paths:

```bash
# decode → tweak one thing → re-encode: closed-loop verification
node -e "
const {decodeCart}=require('./cartdec.js'), {encodeCart}=require('./cartenc.js');
(async()=>{
  const d=await decodeCart('examples/arcade-ping.png');
  const p=Object.assign({}, d.obj, {source: JSON.stringify(d.sources)});
  require('fs').writeFileSync('/tmp/rt.png', encodeCart(p,{width:512,height:424}).png);
})()"
```

Samples built and verified so far: binary assets (allowed since v1.2.0),
`gh:` extensions, locally missing extension, TS syntax errors, too-new
version, verbatim round-trip (`testdata/`).

## Performance

| Stage | Time |
|---|---|
| Decode cartridge | < 0.1 s |
| Copy template `pxt_modules` | ~1.3 s |
| `pxt install` (delta deps) | 1–3 s |
| `pxt build --hwvariant vm` | ~5 s |
| **Total per cartridge** | **~10 s** |

The legacy `tools/png2pxt64.py` took 29 s per cartridge (a full install
every time). The current approach pre-generates a "template project" cache
at packaging time (`pxt_modules` 4MB + `built/dockercross` 1MB); each
conversion copies it and tops up the delta.

## Where the dependency whitelist comes from

`node_modules` holds 577 packages / 405MB, but the actual compile only
touches 60. The whitelist wasn't guessed — it was **measured**:

```js
// Hijack Module._load via NODE_OPTIONS to record every required module
Module._load = function (request) { seen.add(request); return orig.apply(this, arguments); };
```

One real conversion (the most complex cartridge, jumpy) produced 233 module
requests resolving to 58 packages, plus the two target packages read by path
without being required (pxt-arcade / pxt-common-packages) — 60 in total.
Packaging copies **only these 60 top-level packages**: `node_modules`
shrinks from 405MB to 209MB, **85MB** compressed.

## License & trademarks

MIT (see LICENSE). This project is not affiliated with, nor endorsed by,
MakeCode Arcade / Microsoft; MakeCode is a trademark of Microsoft.
