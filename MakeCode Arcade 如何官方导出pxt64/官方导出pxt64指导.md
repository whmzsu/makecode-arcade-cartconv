# MakeCode Arcade 官方在线 IDE 导出 pxt64 游戏卡带——图文指导

> 适用版本：arcade v4.1.27 / Microsoft MakeCode v13.1.24（写作当日的官方线上版本）。
> 全程只需要一个浏览器，无需安装任何东西。

## 这篇文档解决什么问题

MakeCode Arcade 的官方在线 IDE（https://arcade.makecode.com ）默认是「面向硬件」的：
点 **Download** 出来的是烧录到掌机板卡（F4 / R2 等）的 .uf2 固件文件。

但内核存在一个 **VM（虚拟机）目标**——选中它之后，同一个 **Download** 按钮产出的
就不再是固件，而是可以直接运行的 **`.pxt64` 字节码卡带文件**。这个目标目前被归类为
「实验性硬件」，默认隐藏，需要手动开启。

下面按截图逐步操作。

---

## 第 1 步：打开「关于」对话框

打开 https://arcade.makecode.com 首页，点击**右上角的齿轮按钮**（⚙ Settings），
在弹出的菜单中选择 **About...**。

![第1步：右上角齿轮菜单中的 About](2026-11-04%2020%2040%2030.png)

菜单里还有 Language（切界面语言）、Theme（主题）、Reset（重置）等项，都不用动。

## 第 2 步：进入「实验特性」页面

在 **About** 对话框里确认两个版本号（写作时为 `arcade version: 4.1.27`、
`Microsoft MakeCode version: 13.1.24`），然后点击紫色的 **Experiments** 按钮
（不要点绿色的 Ok，那只是关闭对话框）。

![第2步：About 对话框中的 Experiments 按钮](2026-11-04%2020%2040%2043.png)

## 第 3 步：启用 Experimental Hardware（即 VM）

实验页面顶部有黄字警告「WARNING: EXPERIMENTAL FEATURES AHEAD!」。
找到中间那张预览图写着 **VM** 的卡片——**Experimental Hardware**
（描述为 "Enable support for hardware marked 'experimental' in the ..."），
点击卡片右上角的 **Disabled** 标签把它切换为 **Enabled**（标签变绿）。

![第3步：实验列表，红框为 Experimental Hardware（VM）](2026-11-04%2020%2040%2055.png)

## 第 4 步：离开页面让编辑器重载

启用成功后，页面底部会出现横幅：

> **Experiments changed** — The editor will reload when leaving this page.
> （实验已更改 —— 离开此页面时编辑器将重新加载）

不需要找确认按钮，点击左上角的 **← Go back** 返回即可，编辑器会自动刷新一次，
把 VM 目标加载进来。

![第4步：Experimental Hardware 已变 Enabled，底部出现 Experiments changed 横幅](2026-11-04%2020%2041%2004.png)

> 这个开关记录在浏览器本地（localStorage / cookie），对同一浏览器是**持久**的，
> 以后不用重开。换浏览器、清空站点数据或使用隐身窗口后需要重新做第 1～4 步。

## 第 5 步：选择 VM 作为目标硬件

打开（或新建）一个项目进入编辑器，点击**左下角 Download 按钮旁边的「...」小按钮**，
在弹出菜单中选择 **Choose Hardware**（选择硬件）。

![第5步：Download 旁 ... 菜单中的 Choose Hardware](2026-11-04%2020%2041%2050.png)

在硬件列表里会看到三张卡片：**F4**（STM32F4xx 板）、**R2**（Raspberry Pi RP2040 板）、
以及预览只有 "VM" 字样的 **VM** 卡片——选择 **VM**。

![第6步：硬件选择对话框，红框为 VM](2026-11-04%2020%2042%2008.png)

## 第 6 步：点击 Download，得到 .pxt64

选好 VM 后回到编辑器，直接点击左下角的 **Download** 按钮：

![第6步：编辑器左下角 Download 与 ... 按钮](2026-11-04%2020%2048%2030.png)

浏览器会像下载普通文件一样弹出下载提示，文件名格式为
`arcade-<项目名>.pxt64`（例如 `arcade-Magnate-by-Octodemon.pxt64`）。
选择「保存」即可拿到官方编译器输出的 **.pxt64 游戏卡带文件**。

![第7步：浏览器下载 arcade-xxx.pxt64](2026-11-04%2020%2045%2048.png)

> 如果之前选过硬件，菜单里的 **Download as File** 也能达到同样效果——
> 它强制把产物作为文件下载（而不是尝试连接 USB 设备），在 VM 目标下两者等价。

---

## 要点回顾（速查）

| 步骤 | 操作 |
|---|---|
| 1 | 右上角 ⚙ → **About...** |
| 2 | About 对话框 → **Experiments** |
| 3 | 点 **Experimental Hardware** 卡片，Disabled → **Enabled** |
| 4 | **← Go back**，编辑器自动重载 |
| 5 | 编辑器左下 **...** → **Choose Hardware** → 选 **VM** |
| 6 | 点 **Download** → 浏览器保存 `arcade-<项目名>.pxt64` |

## 常见问题

**Q：为什么我的 Download 下载的是 .uf2？**
硬件目标还是 F4/R2，按第 5 步切换到 VM。VM 卡片只有在完成第 1～4 步后才出现在列表里。

**Q：换了浏览器/电脑又要重弄？**
是。实验开关和硬件选择都存在浏览器本地，不跟账号走。

**Q：导出的 .pxt64 有什么用？**
- 可直接加载进支持 pxt64 的播放器/内核运行（如 makecode-arcade-libretro 的 core）；
- 可用于与本地工具链产物做一致性比对（本仓库 `tools/pxt64diff.py` 可逐段对比，
  已验证本地 cartconv 转换产物与官方同版本工具链产物**逐字节一致**）。

**Q：开启实验特性有风险吗？**
VM 目标目前标记为实验性，官方不保证稳定性；但它只改变「编译产物类型」，
不影响你写的项目代码本身。关闭方法与开启相同（再点一次卡片切回 Disabled）。
