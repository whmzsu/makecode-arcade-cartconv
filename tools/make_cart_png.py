#!/usr/bin/env python3
"""把工程目录打成 MakeCode Arcade 的 .png 卡带（纯标准库，无浏览器依赖）。

格式与官方一致，算法逐行照 pxt-core 的 `Util.encodeBlobAsync`
（pxtlib.js）：payload 的比特写进每个像素的 RGB 低 bpp 位，A 通道跳过并置 0xff，
第一个像素的低位存 bpp，紧接 36 字节头（magic / 长度 / addedLines …），
随后是 lzma(alone) 压缩的 {"meta":…, "source":"<文件表 json 字符串>"}。

用法:
    python tools/make_cart_png.py <工程目录> <底图.png|.bmp> <输出.png>
    python tools/make_cart_png.py --verify <输出.png>    # 解回来核对

底图只作缩略图（官方也是拿一张截图当封面），尺寸不够时会整数倍放大以满足容量。
"""

import json
import lzma
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_png_meta import png_to_rgba, extract_payload, payload_to_project  # noqa: E402

MAGIC = 0x59347A7D
HEADER_SIZE = 36
SKIP_DIRS = {"built", "pxt_modules", "node_modules", ".git", ".pxt", "temp"}
SKIP_FILES = {"pxt.json.bak", "tsconfig.json"}


# ---------------- 底图读取 ----------------

def read_bmp24(path):
    d = open(path, "rb").read()
    if d[:2] != b"BM":
        raise ValueError(f"{path}: not a BMP")
    off = struct.unpack_from("<I", d, 10)[0]
    w, h, planes, bits = struct.unpack_from("<iiHH", d, 18)
    if bits != 24 or planes != 1:
        raise ValueError(f"{path}: expect 24-bit BMP, got {bits}-bit")
    flip = h > 0
    h = abs(h)
    row = (w * 3 + 3) & ~3
    px = bytearray(w * h * 3)
    for y in range(h):
        src = off + (h - 1 - y if flip else y) * row
        line = d[src:src + w * 3]
        # BMP 是 BGR，转 RGB
        for x in range(w):
            b, g, r = line[x * 3], line[x * 3 + 1], line[x * 3 + 2]
            o = (y * w + x) * 3
            px[o], px[o + 1], px[o + 2] = r, g, b
    return w, h, bytes(px)


def read_image(path):
    if path.lower().endswith(".bmp"):
        return read_bmp24(path)
    w, h, rgba = png_to_rgba(open(path, "rb").read())
    rgb = bytearray(w * h * 3)
    for i in range(w * h):
        rgb[i * 3:i * 3 + 3] = rgba[i * 4:i * 4 + 3]
    return w, h, bytes(rgb)


def scale_rgb(w, h, rgb, k):
    """最近邻放大 k 倍（封面图不怕糊，格式也不关心插值）。"""
    if k == 1:
        return w, h, rgb
    W, H = w * k, h * k
    out = bytearray(W * H * 3)
    for y in range(H):
        sy = y // k
        for x in range(W):
            sx = x // k
            s = (sy * w + sx) * 3
            o = (y * W + x) * 3
            out[o:o + 3] = rgb[s:s + 3]
    return W, H, bytes(out)


# ---------------- PNG 写出（8 位 RGB，filter 0） ----------------

def write_png(path, w, h, rgb):
    raw = bytearray()
    for y in range(h):
        raw.append(0)                                  # filter type 0
        raw += rgb[y * w * 3:(y + 1) * w * 3]

    def chunk(typ, body):
        return (struct.pack(">I", len(body)) + typ + body
                + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


# ---------------- payload 编码（对齐 encodeBlobAsync） ----------------

def build_payload(proj_dir, name=None, target_ver=None, pxt_ver=None):
    files = {}
    for root, dirs, names in os.walk(proj_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for n in names:
            if n in SKIP_FILES or n.endswith((".png", ".bmp")):
                continue
            full = os.path.join(root, n)
            rel = os.path.relpath(full, proj_dir).replace("\\", "/")
            try:
                files[rel] = open(full, encoding="utf8").read()
            except UnicodeDecodeError:
                continue
    if "pxt.json" not in files:
        raise SystemExit(f"{proj_dir}: 没有 pxt.json")
    pj = json.loads(files["pxt.json"])
    meta = {
        "cloudId": "pxt/arcade",
        "targetVersions": {"target": target_ver or pj.get("targetVersions", {}).get("target", ""),
                           "pxt": pxt_ver or pj.get("targetVersions", {}).get("pxt", "")},
        "editor": "tsprj",
        "name": name or pj.get("name", os.path.basename(proj_dir)),
    }
    text = json.dumps({"meta": meta, "source": json.dumps(files, ensure_ascii=False)},
                      ensure_ascii=False)
    return lzma.compress(text.encode("utf8"), format=lzma.FORMAT_ALONE), meta


def encode_into(w, h, rgb, blob):
    needed = HEADER_SIZE + len(blob)
    usable = (w * h - 1) * 3
    # 上游 pxt 的编码器与解码器在 bpp=3 时互相不一致（实测第 0 字节就错），
    # 真实卡带也只有 bpp 1/2/4 —— 这里跳过 3。
    bpp = 1
    while bpp < 4 and usable * bpp < needed * 8:
        bpp += 1
        if bpp == 3:
            bpp = 4
    if usable * bpp < needed * 8:
        raise SystemExit(f"底图太小：容量 {usable * bpp // 8}B < 需要 {needed}B，请放大底图")

    img = bytearray(w * h * 4)
    for i in range(w * h):
        img[i * 4:i * 4 + 3] = rgb[i * 3:i * 3 + 3]
        img[i * 4 + 3] = 0xFF

    header = struct.pack("<9I", MAGIC, len(blob), 0, 0, 0, 0, 0, 0, 0)

    def enc(ptr, nbits, data):
        shift = 0
        dp = 0
        v = data[dp]
        dp += 1
        mask = (1 << nbits) - 1
        keep = True
        while keep:
            bits = (v >> shift) & mask
            left = 8 - shift
            if left <= nbits:
                if dp >= len(data):
                    if left == 0:
                        break
                    keep = False
                v = data[dp] if dp < len(data) else 0
                dp += 1
                bits |= (v << left) & mask
                shift = nbits - left
            else:
                shift += nbits
            img[ptr] = ((img[ptr] & ~mask) | bits) & 0xFF
            ptr += 1
            if (ptr & 3) == 3:
                img[ptr] = 0xFF
                ptr += 1
        return ptr

    enc(0, 1, bytes([bpp]))          # 第一像素低位存 bpp
    ptr = enc(4, bpp, header)
    enc(ptr, bpp, blob)
    return bpp, img


def make(proj_dir, base_img, out_png, name=None, target_ver=None, pxt_ver=None):
    blob, meta = build_payload(proj_dir, name, target_ver, pxt_ver)
    w, h, rgb = read_image(base_img)
    k = 1
    while (w * k * h * k - 1) * 3 * 4 // 8 < HEADER_SIZE + len(blob):
        k += 1
    W, H, rgb = scale_rgb(w, h, rgb, k)
    bpp, img = encode_into(W, H, rgb, blob)
    flat = bytearray(W * H * 3)
    for i in range(W * H):
        flat[i * 3:i * 3 + 3] = img[i * 4:i * 4 + 3]
    write_png(out_png, W, H, bytes(flat))
    print(f"{os.path.basename(out_png)}: {W}x{H} bpp={bpp} blob={len(blob)}B "
          f"files={len(json.loads(json.loads(lzma.decompress(blob, format=lzma.FORMAT_ALONE))['source']))} "
          f"({os.path.getsize(out_png) / 1024:.0f}KB)")
    return meta


def verify(path):
    w, h, rgba = png_to_rgba(open(path, "rb").read())
    bpp, payload = extract_payload(w, h, rgba)
    comp, obj, sources = payload_to_project(payload)
    print(f"{os.path.basename(path)}: {w}x{h} bpp={bpp} "
          f"{'lzma' if comp else 'plain'} payload={len(payload)}B "
          f"name={obj['meta'].get('name')} files={sorted(sources)}")
    return obj, sources


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--verify":
        verify(sys.argv[2])
        return 0
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    make(sys.argv[1], sys.argv[2], sys.argv[3])
    verify(sys.argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
