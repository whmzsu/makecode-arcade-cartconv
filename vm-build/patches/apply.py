#!/usr/bin/env python3
"""apply.py — npm install 后把 mca-cartconv 补丁重放到 pxt-core

npm install 每次都会把 node_modules 恢复成原版，冲掉 pxt.js 里的
网络下载补丁（codeload 快照 + api.github.com 兜底）。本脚本把
patches/*.js 补丁块整体替换回 pxt.js 对应的 stock 区块。

幂等：pxt.js 里已有补丁标记时跳过。CI（GitHub Actions）和本地重装
node_modules 后都跑这一步。

stock 区块的定界符只匹配当前锁定的 pxt-core 13.2.1。若升级
pxt-core，先核对新版函数边界再改这里的 STOCK_HEAD/STOCK_TAIL。
"""

import glob
import os
import sys

# Windows runner 的 Python 默认 stdout 是 cp1252，print 中文会炸
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PXT_JS = os.path.normpath(
    os.path.join(HERE, "..", "node_modules", "pxt-core", "built", "pxt.js")
)

MARK = "PATCH(mca-cartconv)"

# stock downloadTextAsync 的起止（含尾部导出赋值）。13.2.1 里 stock 实现
# 只有几十行，两个定界符之间的内容整体被补丁块替换。
STOCK_HEAD = "function downloadTextAsync"
STOCK_TAIL = "github.downloadTextAsync = downloadTextAsync;"


def apply_one(patch_path):
    with open(patch_path, encoding="utf8") as f:
        block = f.read()
    if MARK not in block:
        print(f"!! {patch_path} 里没有补丁标记 {MARK}，跳过", file=sys.stderr)
        return False

    with open(PXT_JS, encoding="utf8") as f:
        s = f.read()
    if MARK in s:
        print(f"== 已打过补丁，跳过 {os.path.basename(patch_path)}")
        return True

    a = s.find(STOCK_HEAD)
    b = s.find(STOCK_TAIL)
    if a < 0 or b < a:
        print(
            "!! pxt.js 里找不到 stock downloadTextAsync 区块——pxt-core 版本"
            "可能变了，请核对 apply.py 里的定界符",
            file=sys.stderr,
        )
        sys.exit(2)
    end = b + len(STOCK_TAIL)
    s2 = s[:a] + block + s[end:]
    with open(PXT_JS, "w", encoding="utf8", newline="") as f:
        f.write(s2)
    print(f"== 已重放 {os.path.basename(patch_path)}（{len(s)} -> {len(s2)} 字节）")
    return True


def main():
    if not os.path.isfile(PXT_JS):
        print("!! 找不到 pxt.js——请先在 vm-build 下 npm install", file=sys.stderr)
        sys.exit(1)
    patches = sorted(glob.glob(os.path.join(HERE, "*.js")))
    # codeload-downloadTextAsync.js 本身也是 *.js，这里只收补丁块，
    # apply.py 自己不会被当成补丁（不在 patches/ 目录里被 glob 到）。
    patches = [p for p in patches if os.path.basename(p) != os.path.basename(__file__)]
    if not patches:
        print("!! 没有可重放的补丁", file=sys.stderr)
        sys.exit(1)
    ok = all(apply_one(p) for p in patches)

    # 语法自检：node --check，失败即说明补丁块与当前 pxt-core 不兼容
    import subprocess

    node = os.environ.get("NODE_EXE") or "node"
    chk = subprocess.run([node, "--check", PXT_JS], capture_output=True)
    if chk.returncode != 0:
        print("!! 重放后 pxt.js 语法检查失败：\n" + chk.stderr.decode(errors="replace"))
        sys.exit(3)
    print("== pxt.js 语法检查通过")


if __name__ == "__main__":
    main()
