#!/usr/bin/env python3
"""pxt64diff.py — 两个 .pxt64 镜像的段级对比（纯标准库）

为什么要有它：判断「我们的产物」和「官方 IDE 导出」是否一致，光看文件大小
说明不了任何问题——镜像由一串 section 组成，差异可能只在源码映射、也可能
落在 opcode/API 名字表（这才是与内核兼容性的关键面）。

镜像格式（与 runtime/pxtapp/vm.h 一一对应）：
  每段头 8 字节 = <uint8 type><uint8 flags><uint16 aux><uint32 size>
  size 含头、按 8 字节对齐，段链一直走到文件尾（尾部若有 SRCM 源码映射，
  不属于段链，宿主必须截断后才能喂 VM）。

section 类型：
  0x01 InfoHeader      镜像头（魔数 / 全局槽位 / 时间戳 / 名字）
  0x02 OpCodeMap       opcode 与 API 名字表（\0 分隔）——跨版本兼容的关键
  0x03 NumberLiterals  数字字面量
  0x04 ConfigData      编译期配置
  0x05 IfaceMemberNames 接口成员名
  0x06 NumberBoxes     需装箱的数字（32 位宿主）
  0x20 Function        函数体（字节码）
  0x21 Literal         字面量，aux 区分类型
  0x22 VTable          虚表

用法：
  python tools/pxt64diff.py a.pxt64                  # 单文件结构摘要
  python tools/pxt64diff.py a.pxt64 b.pxt64          # 概览对比
  python tools/pxt64diff.py a.pxt64 b.pxt64 --apis   # 名字表差集（谁多谁少）
  python tools/pxt64diff.py a.pxt64 --list           # 逐段列出
  python tools/pxt64diff.py a.pxt64 --json           # 机器可读摘要

退出码：0 完全相同；1 有差异；2 解析失败。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys

SECTION_TYPES = {
    0x01: "InfoHeader",
    0x02: "OpCodeMap",
    0x03: "NumberLiterals",
    0x04: "ConfigData",
    0x05: "IfaceMemberNames",
    0x06: "NumberBoxes",
    0x20: "Function",
    0x21: "Literal",
    0x22: "VTable",
}


def sname(t: int) -> str:
    return SECTION_TYPES.get(t, f"0x{t:02x}")


class Image:
    """解析后的镜像：段链 + 尾部附加字节。"""

    def __init__(self, path: str):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        self.sections = []  # [(off, type, flags, aux, size, payload)]
        self.trailing = b""
        self.error = None
        self._parse()

    def _parse(self) -> None:
        d = self.data
        off = 0
        while off + 8 <= len(d):
            t, flags, aux, size = struct.unpack_from("<BBHI", d, off)
            if size == 0 or (size & 7) or off + size > len(d):
                tail = d[off:]
                if tail[:4] != b"SRCM":
                    self.error = (f"段链在 {off} 处断开（type=0x{t:02x} size={size}）；"
                                  f"剩余 {len(d) - off} 字节无法识别")
                break
            self.sections.append((off, t, flags, aux, size, d[off + 8:off + size]))
            off += size
        self.trailing = d[off:]

    # ── 派生信息 ──────────────────────────────────────────────────────
    def of_type(self, t: int) -> list:
        return [s for s in self.sections if s[1] == t]

    def info_header(self) -> dict | None:
        secs = self.of_type(0x01)
        if not secs or len(secs[0][5]) < 256:
            return None
        p = secs[0][5]
        magic0, magic1, hex_hash, prog_hash = struct.unpack_from("<QQQQ", p, 0)
        alloc, nonptr = struct.unpack_from("<II", p, 32)
        last_use, install, publish = struct.unpack_from("<QQQ", p, 40)
        image_size = struct.unpack_from("<I", p, 64)[0]
        name = p[128:256].split(b"\0")[0].decode("utf-8", "replace")
        return {
            "magic0": f"0x{magic0:016x}",
            "magic1": f"0x{magic1:016x}",
            "hexHash": f"0x{hex_hash:016x}",
            "programHash": f"0x{prog_hash:016x}",
            "allocGlobals": alloc,
            "nonPointerGlobals": nonptr,
            "lastUsageTime": last_use,
            "installationTime": install,
            "publicationTime": publish,
            "imageSize": image_size,
            "name": name,
        }

    def api_names(self) -> list[str]:
        """OpCodeMap 里的名字表（\0 分隔，按原顺序）。"""
        out: list[str] = []
        for sec in self.of_type(0x02):
            for raw in sec[5].split(b"\0"):
                if raw:
                    out.append(raw.decode("utf-8", "replace"))
        return out

    def summary(self) -> dict:
        hist: dict[str, dict] = {}
        for _off, t, _f, _a, size, _p in self.sections:
            h = hist.setdefault(sname(t), {"count": 0, "bytes": 0})
            h["count"] += 1
            h["bytes"] += size
        return {
            "path": self.path,
            "size": len(self.data),
            "sectionCount": len(self.sections),
            "sections": hist,
            "trailing": len(self.trailing),
            "parseError": self.error,
            "header": self.info_header(),
            "apiCount": len(self.api_names()),
        }


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def print_summary(img: Image) -> None:
    s = img.summary()
    print(f"文件: {s['path']}")
    tail = "SRCM 源码映射（宿主需截断）" if img.trailing[:4] == b"SRCM" else "未知"
    print(f"大小: {s['size']} 字节；段数 {s['sectionCount']}；"
          f"尾部 {s['trailing']} 字节（{tail}）；OpCodeMap 名字 {s['apiCount']} 条")
    if s["parseError"]:
        print(f"  ! {s['parseError']}")
    h = s["header"]
    if h:
        print(f"  头部: name={h['name']!r} magic0={h['magic0']} magic1={h['magic1']}")
        print(f"        hexHash={h['hexHash']} programHash={h['programHash']}")
        print(f"        allocGlobals={h['allocGlobals']} nonPointerGlobals={h['nonPointerGlobals']}"
              f" imageSize={h['imageSize']}")
        print(f"        时间戳: lastUse={h['lastUsageTime']} install={h['installationTime']}"
              f" publish={h['publicationTime']}")
    print("  段类型分布:")
    for name, h2 in sorted(s["sections"].items(), key=lambda kv: -kv[1]["bytes"]):
        print(f"    {name:18} {h2['count']:5} 段  {h2['bytes']:>9} 字节")


def print_list(img: Image) -> None:
    print(f"# {img.path}  共 {len(img.sections)} 段")
    for i, (off, t, flags, aux, size, payload) in enumerate(img.sections):
        print(f"  {i:5} @{off:<8} {sname(t):16} flags={flags} aux={aux:<4} "
              f"size={size:<7} sha={sha(payload)}")


def compare(a: Image, b: Image, deep_apis: bool) -> int:
    sa, sb = a.summary(), b.summary()
    print(f"A: {a.path}  ({sa['size']} 字节, {sa['sectionCount']} 段, "
          f"尾部 {sa['trailing']}{' = SRCM' if a.trailing[:4] == b'SRCM' else ''})")
    print(f"B: {b.path}  ({sb['size']} 字节, {sb['sectionCount']} 段, "
          f"尾部 {sb['trailing']}{' = SRCM' if b.trailing[:4] == b'SRCM' else ''})")

    if a.data == b.data:
        print("\n结果: 逐字节完全相同。")
        return 0

    # 头部字段
    ha, hb = sa["header"], sb["header"]
    if ha and hb:
        diffs = [k for k in ha if ha[k] != hb[k]]
        print(f"\n头部差异: {', '.join(diffs) if diffs else '无'}")
        for k in diffs:
            print(f"  {k}: A={ha[k]!r}  B={hb[k]!r}")

    # 段类型分布
    print("\n段类型对比（count / bytes）:")
    keys = sorted(set(sa["sections"]) | set(sb["sections"]))
    for k in keys:
        x = sa["sections"].get(k, {"count": 0, "bytes": 0})
        y = sb["sections"].get(k, {"count": 0, "bytes": 0})
        mark = "" if x == y else "   <-- 不同"
        print(f"  {k:18} A {x['count']:5}/{x['bytes']:>9}   B {y['count']:5}/{y['bytes']:>9}{mark}")

    # 同类型段的载荷逐段比对（顺序对齐）
    print("\n逐段载荷比对:")
    for t in sorted({s[1] for s in a.sections} | {s[1] for s in b.sections}):
        la, lb = a.of_type(t), b.of_type(t)
        same = sum(1 for x, y in zip(la, lb) if x[5] == y[5])
        print(f"  {sname(t):18} 相同 {same}/{max(len(la), len(lb))} 段"
              f"（A {len(la)} 段 / B {len(lb)} 段）")

    # 名字表差集
    if deep_apis:
        na, nb = a.api_names(), b.api_names()
        only_a = [n for n in na if n not in set(nb)]
        only_b = [n for n in nb if n not in set(na)]
        print(f"\nOpCodeMap 名字表: A {len(na)} 条 / B {len(nb)} 条")
        print(f"  仅 A 有 {len(only_a)} 条" + (f": {', '.join(only_a[:20])}" if only_a else ""))
        print(f"  仅 B 有 {len(only_b)} 条" + (f": {', '.join(only_b[:20])}" if only_b else ""))
        same_order = na == nb
        print(f"  顺序完全一致: {'是' if same_order else '否'}")

    print("\n结果: 有差异（细节见上）。")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description=".pxt64 段级对比")
    ap.add_argument("a", help="镜像 A")
    ap.add_argument("b", nargs="?", help="镜像 B（省略则只看 A 的结构）")
    ap.add_argument("--apis", action="store_true", help="对比 OpCodeMap 名字表差集")
    ap.add_argument("--list", action="store_true", help="逐段列出（单文件模式）")
    ap.add_argument("--json", action="store_true", help="输出机器可读摘要")
    args = ap.parse_args()

    try:
        a = Image(args.a)
    except OSError as e:
        print(f"读取失败: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(a.summary(), ensure_ascii=False, indent=2))
        return 0
    if args.list:
        print_list(a)
        return 0
    if not args.b:
        print_summary(a)
        return 0

    try:
        b = Image(args.b)
    except OSError as e:
        print(f"读取失败: {e}", file=sys.stderr)
        return 2
    return compare(a, b, args.apis)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认 cp936
    raise SystemExit(main())
