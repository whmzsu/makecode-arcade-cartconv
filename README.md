# cartconv — MakeCode Arcade 卡带转换器

把 MakeCode Arcade 保存的 `.png` 卡带转换成 `.pxt64` 字节码镜像，供
[makecode-arcade-libretro](https://github.com/whmzsu/makecode-arcade-libretro)
（RetroArch 的 MakeCode Arcade 核心）直接运行。

给玩家的是**免安装便携包**：解压后把 `.png` 拖到 `cartconv.exe` 上即可，
不需要装 Node.js、npm 或 Python。便携包见本仓库 Releases。

## 快速开始

**便携包（推荐）**：下载 Releases 里的 `makecode-cartconv-<ver>-windows-x64.zip`，
解压后拖拽 `.png`（支持单个 / 多选 / 整个文件夹）。

**源码直跑**（任何平台，需 Node.js ≥ 16）：

```bash
npm install          # 在 vm-build/ 下装 pxt 编译链（锁文件锁定版本）
node cartconv.js game.png
node cartconv.js carts/ -o out/     # 批量
```

转换结果 `.pxt64` 放进掌机，在 RetroArch 里加载即可。

## 为什么需要转换

`.png` 卡带里只有**项目源码**（`meta` + `source`，用 4 张真实卡带验证过），
没有编译产物。要变成 core 能执行的 VM 字节码，必须现场过一遍 pxt 编译器
（`pxt build --hwvariant vm`）。这就是这个工具的重量来源——绕不开 node + pxt。

## 支持范围：别指望 100%

**已验证的只有 4 张真实卡带**：ping、jumpy、falling duck、cube land
（ping 在 `examples/`）。覆盖 bpp=1/2、blocks/TS 两种编辑器、含中文源码、
依赖 animation 与 color-coded-tilemap 的工程。

除此之外的卡带没有样本，也就没有保证。已知转不了的情况分四类，工具会主动识别
并说明原因：

| 情况 | 工具表现 | 说明 |
|---|---|---|
| 依赖社区扩展 `gh:user/repo` | 编译前拦下 | 需要联网下载，离线包做不到 |
| 本地没有的扩展名 | `install` 后核对，报出缺哪个 | 官方扩展离线可用，第三方不行 |
| 源码含二进制资源 | 编译前拦下 | 见下 |
| 卡带比编译器新 | 警告但继续编译 | 本地 pxt-arcade 4.2.1 |

### 二进制资源为什么转不了

新版 MakeCode（2023 之后的 assets 系统）会把用户上传的图片、音效作为独立文件
存进工程。这类文件按当前实现会用 `utf8` 写出，二进制内容被破坏，编译出的结果是
错的——而且**不会有任何报错**。所以宁可拦下也不能放行。

真遇到这种卡带，让作者在 MakeCode 里用 libretro 导出的 `.pxt64`，或者把工程分享
链接给出来用网页版编译。

### 版本兼容的方向性

已验证卡带的 `meta.targetVersions` 都是 `target 1.3.44 / pxt 6.8.33`，
本地编译器是 `pxt-arcade 4.2.1 / pxt-core 13.2.1`——**新编译器跑旧卡带**成立。
反过来不成立：如果卡带用了 4.2.1 之后新增的接口，编译会失败，这时预检会给出
版本警告作为线索。

## 目录结构

```
cartconv.js          主程序（参数解析、批量、进度、调用编译器）
cartdec.js           .png 卡带解码（PNG → 位流 → LZMA → 项目 JSON）
cartenc.js           卡带编码（仅测试用，不进包）
precheck.js          编译前预检（二进制资源 / 社区扩展 / 版本）
launcher.c           Windows 拖拽入口（zig cc 编译成 cartconv.exe）
fakebin/docker.cmd   docker 假程序（pxt 编译流程会尝试调 docker）
keep_modules.txt     依赖白名单（实测生成，见下）
prune_modules.py     按白名单裁剪**已有**目录（打包已改用正向复制，此脚本留作校验）
package_cartconv.sh  打便携包
package.json         版本号（打包脚本读取）
vm-build/            pxt 编译链依赖清单（package.json + 锁文件；node_modules 不入库）
tools/png2pxt64.py   旧版转换脚本（29s/张，留作 cartconv 的参照实现）
tools/extract_png_meta.py  .png 卡带格式解析（纯 Python，cartdec.js 与其逐字节等价）
examples/            验证样本
testdata/            故障样本（预检拦截路径的回归）
```

## 测试样本怎么造

`cartenc.js` 是 `cartdec.js` 的反向实现：工程对象 → `.png` 卡带。位流算法逐行
照搬 pxt 的 `Util.encodeBlobAsync`，只差 PNG 容器用 zlib 写。

它存在的意义是造故障样本——真实卡带覆盖不到那些失败路径：

```bash
# 解码 → 改一处 → 重新编码，闭环验证
node -e "
const {decodeCart}=require('./cartdec.js'), {encodeCart}=require('./cartenc.js');
(async()=>{
  const d=await decodeCart('examples/arcade-ping.png');
  const p=Object.assign({}, d.obj, {source: JSON.stringify(d.sources)});
  require('fs').writeFileSync('/tmp/rt.png', encodeCart(p,{width:512,height:424}).png);
})()"
```

已造过并验证过拦截效果的样本：二进制资源、`gh:` 扩展、本地缺扩展、TS 语法错误、
版本偏新、原样往返（`testdata/`）。

## 性能

| 阶段 | 耗时 |
|---|---|
| 解码卡带 | < 0.1s |
| 复制模板 `pxt_modules` | ~1.3s |
| `pxt install`（补差量依赖） | 1~3s |
| `pxt build --hwvariant vm` | ~5s |
| **单张合计** | **约 10s** |

旧脚本 `tools/png2pxt64.py` 每张要 29 秒（每次都完整 install）。现在的做法是
打包时预生成一份"模板工程"缓存（`pxt_modules` 4MB + `built/dockercross` 1MB），
每次转换复制一份再补差量。

## 依赖白名单怎么来的

`node_modules` 有 577 个包、405MB，但实际编译只用得到 60 个。
白名单不是猜的，是**实测**的：

```js
// 用 NODE_OPTIONS 劫持 Module._load，记录所有被 require 的模块
Module._load = function (request) { seen.add(request); return orig.apply(this, arguments); };
```

跑一次真实转换（用最复杂的 jumpy 卡带），得到 233 条模块请求、解析出 58 个包，
再加上 pxt-arcade / pxt-common-packages 两个"按路径读取、不 require"的目标包，
共 60 个。打包时**只复制这 60 个顶层包**，`node_modules` 从 405MB 降到 209MB，
压缩后 **85MB**。

## 许可与商标

MIT（见 LICENSE）。本项目与 MakeCode Arcade / Microsoft 无隶属关系，
亦未获其认可；MakeCode 是 Microsoft 的商标。
