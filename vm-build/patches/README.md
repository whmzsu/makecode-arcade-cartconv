# vm-build/patches

node_modules 是 gitignore 的，npm install 会冲掉对 pxt 包的手工修改，
所以补丁以文本形式保存在这里，升级/重装后重新套用。

## 重放

    python patches/apply.py

幂等（已打过则跳过），自带 node --check 语法自检。GitHub Actions 的
打包流程（.github/workflows/package.yml）在 npm install 后自动跑。

## codeload-downloadTextAsync.js

套用位置：`node_modules/pxt-core/built/pxt.js`，
把 stock 的 `function downloadTextAsync ... github.downloadTextAsync = downloadTextAsync;`
整段替换为本文件内容（内含重写的 downloadTextAsync + 新增 codeloadTextAsync）。

背景：raw.githubusercontent.com 在部分网络下 TLS 握手直接死（ECONNRESET），
连接层报错不会走 api.github.com contents 兜底。补丁改为 codeload.github.com
整仓 zip 快照优先（进程内按 (repo, commit) 缓存），失败再依次回退
raw / contents API。gh: 社区扩展的在线下载全靠它。

## codeload-tagToSha.js

套用位置：同文件，替换 stock 的 `function tagToShaAsync ... async function
pkgConfigAsync` 之间的内容（保留下一函数起点作定界）。

背景：pxt 下载 `github:user/repo#tag` 之前，会先打
`api.github.com/repos/<slug>/git/refs/tags/<tag>`（失败再试 heads）把 tag
解析成 40 位 sha。这个端点**未认证时只有 60 次/小时**，超限返回 403，pxt
直接抛 `Got HTTP 403. Did you forget to pxt login ?`，整个 install 失败。
一个挂了 8~14 个扩展的游戏就能把配额打光（实测批量扫 59 个社区工程时触发，
32 个项目因此失败）。

修法：解析失败（403/401/网络错）时把 ref 原样返回。codeload 的
`/zip/<ref>` 端点本来就接受分支名和 tag 名，不需要先转成 sha，后续文件
下载走上面的 codeload 快照补丁。**用户不需要 GitHub token，也不再受
API 限流影响**（加上这块之前，每次换 IP 都要 `pxt login` 才能批量转扩展卡带）。

注意：没有显式版本号的依赖（`gh:user/repo` 不带 `#tag`）仍会走
`latestVersionAsync` 去问 api.github.com 的 tags 列表，限流时依旧会失败——
现有真实卡带语料里没有这种写法。

## 为什么 pxt-core 停在 13.2.1（2026-11-03 实验结论）

尝试升级 pxt-core 13.2.13 + pxt-common-packages 14.2.1（pxt-arcade master
的 pin）失败：13.2.13 编译器会对字符串下标赋值发射新 VM 函数
`pxtrt::mapSetByStringOnly`（_pxt_map_set_by_string），而最新发布的运行时
（common-packages 14.2.1 的 core---vm，310 个函数）没有实现它，VM 校验
TS9200 直接失败。上游 master 的组合依赖未发版的运行时组件，npm 装不到；
且 .pxt64 最终跑在 libretro core 的旧版 VM 上，core 也没有这个函数——
校验器拦下是对的。**pxt-arcade 4.2.1 官方配对 13.2.1/14.1.4 就是 npm 可得
的最新一致组合，升级需等上游发版。**
