#!/usr/bin/env python3
"""apply.py — npm install 后把 mca-cartconv 补丁重放到 pxt-core

npm install 每次都会把 node_modules 恢复成原版，冲掉 pxt.js 里的网络补丁。
本脚本把 patches/*.js 补丁块整体替换回 pxt.js 对应的 stock 区块。

目前有两块补丁，都只跟「能不能在受限网络拉到 github: 扩展」有关：

1. codeload-downloadTextAsync.js
   raw.githubusercontent.com 在部分网络不可达（TLS 握手 ECONNRESET），
   改为从 codeload.github.com 拉整个仓库快照，按文件路径从内存取。

2. codeload-tagToSha.js
   pxt 下载扩展前会先打 api.github.com 的 git/refs 把 tag 解析成 sha。
   未认证调用限流 60 次/小时，超限即 403，pxt 报
   "Got HTTP 403. Did you forget to pxt login ?" 并让整个 install 失败。
   codeload 的 zip 端点本来就接受 tag/分支名，所以解析失败时直接把 ref
   原样返回（不再要求有 GitHub token）。

幂等：pxt.js 里已有该补丁的标记时跳过。CI（GitHub Actions）和本地重装
node_modules 后都跑这一步。

定界符只匹配当前锁定的 pxt-core 13.2.1。若升级 pxt-core，先核对新版函数
边界再改这里的 PATCH_SPECS。
"""

import os
import subprocess
import sys

# Windows runner 的 Python 默认 stdout 是 cp1252，print 中文会炸
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PXT_JS = os.path.normpath(
    os.path.join(HERE, "..", "node_modules", "pxt-core", "built", "pxt.js")
)

# 每块补丁：文件、stock 区块起止定界符、幂等标记。
#   replace='block'  —— 把 [head, tail] 整段（含 tail）换成补丁块
#   replace='before' —— 只把 [head, tail) 换掉，tail 那行保留（用作下一函数的起点）
PATCH_SPECS = [
    {
        "file": "codeload-downloadTextAsync.js",
        "head": "function downloadTextAsync",
        "tail": "github.downloadTextAsync = downloadTextAsync;",
        "replace": "block",
        "mark": "PATCH(mca-cartconv)",
    },
    {
        "file": "codeload-tagToSha.js",
        "head": "function tagToShaAsync",
        "tail": "async function pkgConfigAsync",
        "replace": "before",
        "mark": "PATCH(mca-cartconv:tagref)",
    },
]


def apply_one(spec, s):
    patch_path = os.path.join(HERE, spec["file"])
    if not os.path.isfile(patch_path):
        print(f"!! 找不到补丁 {spec['file']}", file=sys.stderr)
        return s, False
    if spec["mark"] in s:
        print(f"== 已打过 {spec['file']}，跳过")
        return s, True

    with open(patch_path, encoding="utf8") as f:
        block = f.read()
    if spec["mark"] not in block:
        print(f"!! {spec['file']} 里没有补丁标记 {spec['mark']}", file=sys.stderr)
        return s, False

    a = s.find(spec["head"])
    b = s.find(spec["tail"], a + 1) if a >= 0 else -1
    if a < 0 or b < a:
        print(
            f"!! pxt.js 里找不到 {spec['head']!r} 的 stock 区块——pxt-core 版本"
            "可能变了，请核对 apply.py 里的 PATCH_SPECS",
            file=sys.stderr,
        )
        sys.exit(2)

    end = b + len(spec["tail"]) if spec["replace"] == "block" else b
    s2 = s[:a] + block + s[end:]
    print(f"== 已重放 {spec['file']}（{len(s)} -> {len(s2)} 字节）")
    return s2, True


def main():
    if not os.path.isfile(PXT_JS):
        print("!! 找不到 pxt.js——请先在 vm-build 下 npm install", file=sys.stderr)
        sys.exit(1)

    with open(PXT_JS, encoding="utf8") as f:
        s = f.read()
    orig_len = len(s)

    ok = True
    for spec in PATCH_SPECS:
        s, good = apply_one(spec, s)
        ok = ok and good

    if not ok:
        sys.exit(1)
    if len(s) != orig_len:
        with open(PXT_JS, "w", encoding="utf8", newline="") as f:
            f.write(s)

    # 语法自检：node --check，失败即说明补丁块与当前 pxt-core 不兼容
    node = os.environ.get("NODE_EXE") or "node"
    chk = subprocess.run([node, "--check", PXT_JS], capture_output=True)
    if chk.returncode != 0:
        print("!! 重放后 pxt.js 语法检查失败：\n" + chk.stderr.decode(errors="replace"))
        sys.exit(3)
    print("== pxt.js 语法检查通过")


if __name__ == "__main__":
    main()
