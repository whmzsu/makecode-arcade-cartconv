[English](README.en.md) | 简体中文

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

## 另一种选择：不装工具，用官方在线 IDE 导出

便携包约 80MB，只是偶尔转一两张卡带的话，其实可以什么都不装——官方在线 IDE
里就有导出 `.pxt64` 的开关，全程在浏览器完成：

1. 打开 <https://arcade.makecode.com>，把 `.png` 卡带**拖进页面**（或首页 **Import**
   导入文件）；
2. 右上角齿轮 ⚙ → **About...** → 点紫色 **Experiments** 按钮；
3. 把中间那张预览写着 **VM** 的 **Experimental Hardware** 卡片从 `Disabled`
   点成 **Enabled**，再点左上角 **← Go back**（编辑器会自动重载）；
4. 编辑器左下 **Download 旁边的 `...`** → **Choose Hardware** → 选 **VM**；
5. 点 **Download**，浏览器直接下载 `arcade-<项目名>.pxt64`。

每步截图见
[`MakeCode Arcade 如何官方导出pxt64/官方导出pxt64指导.md`](MakeCode%20Arcade%20如何官方导出pxt64/官方导出pxt64指导.md)
（[English version](MakeCode%20Arcade%20如何官方导出pxt64/官方导出pxt64指导.en.md)）。

**两边产出是同一份东西**：同一张卡带，官方线上工具链（写作时 `arcade 4.1.27 /
pxt 13.1.24`）与本工具内置链（`4.2.1 / 13.2.1`）编出的 `.pxt64` **逐字节一致**
——已在 ping、jumpy-platformer、community-falling-duck、strawberry-slam 四例上
验证（最后一例带 6 个 GitHub 扩展），连段数和 SRCM 尾部长度都相同。

两者怎么取舍：

| | 官方在线 IDE | 本工具 |
|---|---|---|
| 安装 | 不需要，开网页即可 | 下载约 80MB 便携包 |
| 批量 | 一张张手动点 | 拖一个文件夹，或命令行 |
| 离线 | 不行 | 可以（`--no-net`） |
| 出错时 | 编译器原始报错 | 预检给中文原因与处理建议 |
| 社区扩展 | 由浏览器现拉 GitHub | 内置 codeload / api 兜底补丁 |

一句话：**偶尔转一两张，官方 IDE 更省事；要批量、离线，或卡在社区扩展下载上，
用本工具。**

## 为什么需要转换

`.png` 卡带里只有**项目源码**（`meta` + `source`，21 张真实卡带均如此），
没有编译产物。要变成 core 能执行的 VM 字节码，必须现场过一遍 pxt 编译器
（`pxt build --hwvariant vm`）。这就是这个工具的重量来源——绕不开 node + pxt。

## 支持范围：21 张真实卡带已验证（但别指望 100%）

2026 年 11 月做过一轮完整回归，共 21 张卡带，语料在
[makecode-arcade-libretro](https://github.com/whmzsu/makecode-arcade-libretro)
仓库的 `png_examples/`：

- **4 张官方示例**（ping / jumpy-platformer / falling-duck / cube-land）——
  从官网下载的原生 `.png` 卡带，未做任何改动；
- **17 个真实社区项目**——项目源码从官方分享链接取回，再用本项目
  `tools/make_cart_png.py` 按官方格式回打成 `.png`（封面取核心实跑截帧），
  用来覆盖较新的编辑器特性与大量社区扩展。

| 维度 | 结果 |
|---|---|
| 转换 | **21 / 21 成功**，0 失败 0 跳过，总耗时约 603 秒 |
| 编解码闭环 | 17 张回打样本转回 `.pxt64` 后，与打包前的原产物 **sha256 逐字节一致**（png 编解码无损） |
| 可运行性 | 产物灌进 libretro core 跑 600 帧，**19 张正常**（两例异常见下，均非转换器问题） |
| 覆盖面 | bpp=1/2、积木与 TS 两种编辑器、含中文源码、二进制资源工程 |

其中 **8 张依赖 GitHub 社区扩展**（`gh:` / `github:` 写法都有），最多一张挂了
9 个扩展，合计 22 个不同版本引用——联网模式下全部现场下载并编译通过。

17 个社区项目是：blocky-boss-battle、bunny-hop、caterpillar、cave-explorer、
falling-duck、galgamulti、hot-air-balloon、jewel-raider、kickoff、mouse-adventure、
pigeon-deliverance、save-the-forest、secure-the-river、space-destroyer、
stack-the-goats、strawberry-slam、tictactwo。

### 两个已知异常（都不是转换器的问题）

| 卡带 | 现象 | 定性 |
|---|---|---|
| mouse-adventure | 无输入时画面静止，冒烟判为 `static` | **误报**。抓帧确认是正常关卡画面（砖墙+老鼠），按键后角色正常移动 21 个不同画面——这游戏无输入时本来就不动 |
| strawberry-slam | 约 5.1 秒后 VM panic 980（`PANIC_CAST_FROM_NULL`，对 null 调方法），与输入无关、时间点固定 | **疑似游戏自身 bug**：源码里有 `game.runtime()+5000` 的倒计时逻辑。与 castle 黑屏同类，不是转换链引入的 |

复现这两个结论要注意：冒烟必须指向 `core/dist/<target>/` 下的最新 DLL。core 根
目录那份 0.2.15 旧构建在 panic 时会带崩宿主（`0xc0000005`），会被误判成崩溃；
0.3.1 起 panic 后宿主存活，判定才是 `panic`。

再往外就没有样本了，也就没有保证。被验证卡带之外的已知限制分四类，工具会主动
识别并说明原因：

| 情况 | 工具表现 | 说明 |
|---|---|---|
| 依赖社区扩展 `gh:user/repo` | 能连 GitHub 就联网下载编译；连不上则编译前拦下 | 见下 |
| 本地没有的扩展名 | `install` 后核对，报出缺哪个 | 官方扩展离线可用，第三方不行 |
| 源码含二进制资源 | 原样写回工程，警告后继续编译 | 见下 |
| 卡带比编译器新 | 警告但继续编译 | 本地 pxt-arcade 4.2.1 |

### 社区扩展与联网（v1.2.0 起）

卡带用到社区扩展时（`"gh:user/repo"` 或 `"pkg": "github:user/repo#tag"` 两种写法
都识别），cartconv 会先探测 GitHub 连通性（codeload.github.com 主通道 +
api.github.com 兜底，6 秒超时）：

- **连得上** → 放行，`pxt install` 现场从 GitHub 下载扩展再编译。下载失败
  （仓库不存在、网络抖动）会在报错里说明是下载问题，不会伪装成其他错误；
- **连不上** → 编译前拦下并说明缺什么，避免一句没信息量的 pxt 报错；
- `--no-net` 可强制按离线处理（跳过探测）。

内置编译链对扩展下载通道打过补丁：raw.githubusercontent.com 不可达时自动改走
codeload 整仓快照，再不行走 api.github.com contents API 逐文件兜底。

另外，pxt 下载 `github:repo#tag` 前本来要调 api.github.com 把 tag 解析成 commit
（**未认证只有 60 次/小时**，超限就报 `Got HTTP 403. Did you forget to pxt login ?`），
现在解析失败时直接用 ref 名走 codeload——所以**不需要 GitHub token，也不受 API
限流影响**。只有一个挂了十来个扩展的卡带才会明显感到差别，但撞上限流时报错很难懂。

`testdata/net-ghdep.png` 是声明了真实社区扩展的样本卡带（联网时转换成功，
离线时按缺扩展拦下）。

### 二进制资源怎么处理（v1.2.0 起）

新版 MakeCode 的 assets 系统会把用户上传的图片、音效作为独立二进制文件存进工程
（`assets/xxx.png` 等）。这些文件以 latin1 逐字节映射存在卡带里，cartconv 会按
原样（字节级还原）写进编译工程再编译——不再拦截。

要说明的是边界：**本地 pxt 编译器只消费 `.ts`/`.jres` 等文本资源**，独立的二进制
资产文件对它是惰性的。所以：

- 源码只引用编辑器绘制的图形（存在 `*.g.jres` 里）→ 正常编译，二进制文件只是跟着
  躺在工程里；
- 源码引用了必须由二进制文件参与编译的资产（如上传的 PNG 精灵未被转成 jres）→
  编译器会报错或运行缺图。预检会静态核对 `assets.image\`名字\`` 这类引用在工程
  `.jres` 里是否存在，对不上时给出警告作为排查线索。

### 版本兼容的方向性

先说清 `meta.targetVersions` 是什么：它记录**卡带被打包那一刻**的工具链版本，
既不代表文件新旧，也不等于你眼前编辑器的版本。

| 语料 | `meta.targetVersions` | 这个数字怎么来的 |
|---|---|---|
| 4 张官方示例 | `target 1.3.44 / pxt 6.8.33` | 官方 **2021-02** 打包这批示例时写入（pxt-arcade 1.3.44 发布于 2021-02-05）。文件是官网现在仍在提供的那一份，只是官方一直没拿新版重打包 |
| 17 个社区回打样本 | `target 4.2.1 / pxt 13.2.1` | 由 `tools/make_cart_png.py` 回打时按**本地链**写入，并非官方编辑器所写 |
| （参照）当前官方在线编辑器 | `target 4.1.27 / pxt 13.1.24` | 2026-10 的 stable4.1 分支；本工具链 `4.2.1 / 13.2.1` 反而更新 |

真正的兼容结论是：**`pxt 6.8.33 → 13.2.1` 这段跨度都跑得通**——2021 年的卡带
能被四年后的编译器吃下，说明老接口没有被删；同代更不用说。反过来不保证：卡带
若用了比 4.2.1 更新的接口，编译会失败，预检会给出版本警告作为线索。

另外，17 张回打样本的版本戳本来就是本地链写进去的，所以它们转回 `.pxt64`
逐字节一致属于**闭环自检**（证明编解码无损），不能当成"两个独立来源互证"。
独立互证在于另一组实验：同一张卡带在官方同版本链（4.1.27/13.1.24）与本工具链
下编出的产物也逐字节相同，见上一节。

## 目录结构

```
cartconv.js          主程序（参数解析、批量、进度、调用编译器）
cartdec.js           .png 卡带解码（PNG → 位流 → LZMA → 项目 JSON）
cartenc.js           卡带编码（仅测试用，不进包）
precheck.js          编译前预检（社区扩展 / 版本 / 二进制资源放行 / 资产引用核对）
launcher.c           Windows 拖拽入口（zig cc 编译成 cartconv.exe）
fakebin/docker.cmd   docker 假程序（pxt 编译流程会尝试调 docker）
keep_modules.txt     依赖白名单（实测生成，见下）
prune_modules.py     按白名单裁剪**已有**目录（打包已改用正向复制，此脚本留作校验）
package_cartconv.sh  打便携包
package.json         版本号（打包脚本读取）
vm-build/            pxt 编译链依赖清单（package.json + 锁文件；node_modules 不入库）
tools/png2pxt64.py   旧版转换脚本（29s/张，留作 cartconv 的参照实现）
tools/extract_png_meta.py  .png 卡带格式解析（纯 Python，cartdec.js 与其逐字节等价）
tools/pxt64diff.py   .pxt64 段级对比（段类型分布 / OpCodeMap 名字表差集）
tools/make_cart_png.py  工程目录 → 官方格式 .png 卡带（造回归语料 / 往返校验）
tools/fetch_shared.py   官方分享 id → 工程源码 → .pxt64（批量收真实游戏）
examples/            验证样本
testdata/            故障样本（预检拦截路径的回归）
MakeCode Arcade 如何官方导出pxt64/  官方 IDE 导出 .pxt64 的图文指导与截图
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

已造过并验证过效果的样本：二进制资源（v1.2.0 起放行）、`gh:` 扩展、本地缺扩展、
TS 语法错误、版本偏新、原样往返（`testdata/`）。

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
