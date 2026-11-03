"""fetch_shared.py — 从 MakeCode 分享 id 拉取整套工程，编译成 .pxt64 测试卡带

用途：批量收集**真实游戏**做回归语料。分享链接
``https://arcade.makecode.com/---<shortid>`` 的项目源码可以从
``https://arcade.makecode.com/api/<shortid>/text`` 直接取到完整文件表
（main.ts / main.blocks / pxt.json / tilemap.g.jres ...），比 .png 卡带更完整
（卡带只有 meta+source，这里连资源文件都有）。之后的编译路径与
``png2pxt64.py`` 完全一致，产物同样是 core 能直接加载的 VM 字节码镜像。

用法：
  python tools/fetch_shared.py _Y8VUmcHYsdsy -o carts/
  python tools/fetch_shared.py --manifest GameList.json -o carts/
  python tools/fetch_shared.py --manifest GameList.json --only Galga,Stop -o carts/

注意：分享 id 的有效性由官方站点决定，取不到会明确报 404，不会静默跳过。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from png2pxt64 import (  # noqa: E402  复用同一套编译路径
    TARGET,
    ensure_docker_stub,
    run_pxt,
    write_project,
)

API = "https://arcade.makecode.com/api/"


def fetch_sources(shortid: str, timeout: int = 30) -> dict:
    """取分享项目的全部源文件；dependencies 里的扩展由 pxt install 负责下载。"""
    url = API + shortid + "/text"
    req = urllib.request.Request(url, headers={"User-Agent": "fetch_shared/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf8")
    try:
        files = json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(f"{shortid}: 返回的不是 JSON（{len(raw)} 字节）: {raw[:200]}")
    if not isinstance(files, dict) or "pxt.json" not in files:
        raise SystemExit(f"{shortid}: 文件表异常: {list(files)[:8]}")
    return files


def safe_name(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def build_one(shortid: str, name: str, out_dir: str, verbose: bool = False) -> dict:
    sources = fetch_sources(shortid)
    total = sum(len(v) for v in sources.values())
    print(f"[1/3] {name}: {len(sources)} 个文件 / {total} 字符  ({shortid})")

    proj_dir = os.path.join(TARGET, "proj_" + name)
    write_project(proj_dir, sources)

    proc = run_pxt(["install", "--hwvariant", "vm"], proj_dir)
    if proc.returncode != 0 or not os.path.isdir(os.path.join(proj_dir, "pxt_modules", "device")):
        sys.stderr.write(proc.stdout[-2000:] + "\n" + proc.stderr[-2000:])
        raise SystemExit(f"[2/3] {name}: pxt install 失败"
                         f"（多半是依赖的社区扩展取不到，检查 codeload/网络）")

    proc = run_pxt(["build", "--hwvariant", "vm"], proj_dir)
    image = os.path.join(proj_dir, "built", "binary.pxt64")
    if not os.path.isfile(image) and ensure_docker_stub(proj_dir):
        proc = run_pxt(["build", "--hwvariant", "vm"], proj_dir)
    if verbose:
        sys.stderr.write(proc.stdout[-3000:])
    if not os.path.isfile(image):
        sys.stderr.write(proc.stdout[-2000:] + "\n" + proc.stderr[-2000:])
        raise SystemExit(f"[3/3] {name}: 编译未产出 binary.pxt64")

    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, name + ".pxt64")
    shutil.copyfile(image, dst)
    size = os.path.getsize(dst)
    print(f"[3/3] {name}: {dst} ({size} 字节)")
    return {
        "id": shortid,
        "name": name,
        "cart": os.path.basename(dst),
        "image_bytes": size,
        "files": sorted(sources),
        "deps": sorted(json.loads(sources["pxt.json"]).get("dependencies", {})),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="分享 id → .pxt64 测试卡带")
    ap.add_argument("ids", nargs="*", help="分享 id（可多个），如 _Y8VUmcHYsdsy")
    ap.add_argument("--manifest", help="含 games[] 的 JSON（官方 docs/GameList.json 格式）")
    ap.add_argument("--only", help="逗号分隔的名字过滤（大小写不敏感，子串匹配）")
    ap.add_argument("-o", "--out", required=True, help="输出目录")
    ap.add_argument("--keep-project", action="store_true", help="保留中间工程")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    todo: list[tuple[str, str]] = []
    if args.manifest:
        with open(args.manifest, encoding="utf8") as f:
            games = json.load(f)["games"]
        for g in games:
            todo.append((g["id"], safe_name(g["name"])))
    for sid in args.ids:
        todo.append((sid, safe_name(sid)))
    if not todo:
        ap.error("至少给一个 id，或用 --manifest")

    if args.only:
        keys = [k.strip().lower() for k in args.only.split(",") if k.strip()]
        todo = [(i, n) for i, n in todo if any(k in n.lower() for k in keys)]

    ok, failed = [], []
    for sid, name in todo:
        try:
            ok.append(build_one(sid, name, args.out, args.verbose))
        except SystemExit as e:
            print(f" !! {name}: {e}", file=sys.stderr)
            failed.append({"id": sid, "name": name, "error": str(e)})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f" !! {name}: 取源码失败 {e}", file=sys.stderr)
            failed.append({"id": sid, "name": name, "error": str(e)})
        if not args.keep_project:
            shutil.rmtree(os.path.join(TARGET, "proj_" + name), ignore_errors=True)

    os.makedirs(args.out, exist_ok=True)
    index = os.path.join(args.out, "index.json")
    payload = {"built": ok, "failed": failed}
    if os.path.isfile(index):
        # 追加模式：分批收集时不要把之前的记录覆盖掉
        try:
            old = json.load(open(index, encoding="utf8"))
            seen = {x["name"] for x in ok}
            payload["built"] = [x for x in old.get("built", []) if x["name"] not in seen] + ok
            payload["failed"] = [x for x in old.get("failed", [])
                                 if x["name"] not in {y["name"] for y in failed}] + failed
        except (json.JSONDecodeError, OSError):
            pass
    with open(index, "w", encoding="utf8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    print(f"\n完成 {len(ok)} 张，失败 {len(failed)} 张；索引 {index}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
