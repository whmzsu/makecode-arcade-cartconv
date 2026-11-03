'use strict';
/*
 * 编译前预检 —— 在真正跑 pxt 编译器之前，把注定失败、或大概率出问题的卡带挑出来。
 *
 * 为什么需要：pxt 编译失败时的原始输出是给开发者看的（TypeScript 报错、缺包栈），
 * 玩家看不懂，也没法自助解决。更糟的是 install 阶段缺扩展会被后来的 build 报错
 * 掩盖成一句"编译失败"，连排查方向都没有。
 *
 * 预检只做**能确定**的判断，拿不准的一律放过交给编译器，避免误杀。
 */

const fs = require('fs');
const path = require('path');

/* 卡带里正常出现的文本文件扩展名。不在表里的按可疑处理，但不直接判死。 */
const TEXT_EXT = new Set([
  '.ts', '.json', '.md', '.markdown', '.blocks', '.jres', '.js',
  '.txt', '.csv', '.svg', '.css', '.html', '.htm', '.xml',
  '.yml', '.yaml', '.ini', '.cfg',
]);

/* 明确是二进制格式的扩展名 —— 出现在卡带源码里说明是资源文件 */
const BIN_EXT = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico',
  '.wav', '.mp3', '.ogg', '.m4a', '.flac',
  '.zip', '.bin', '.dat', '.ttf', '.otf', '.woff', '.woff2',
]);

/*
 * 是不是二进制内容。
 *
 * 卡带里的文件都是 JSON 字符串，二进制资源以 latin1 式逐字节映射存进来，
 * 于是会出现 C0 控制字符或 UTF-8 替换字符。正常的源码里只可能有 \t \n \r
 * 三种控制字符。返回 null 表示文本，否则给一句人话原因。
 */
function looksBinary(s) {
  if (typeof s !== 'string') return '内容不是字符串';
  if (s.indexOf('\ufffd') >= 0) return '含非法 UTF-8 序列';
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(s)) return '含二进制控制字符';
  return null;
}

/*
 * 落盘判定：该文件按二进制（latin1 → 原始字节）写出还是按文本（utf8）写出。
 *
 * 规则：扩展名明确是二进制格式，或内容检测出二进制特征 → 按二进制写。
 * 之前这里直接 fatal 拒收整张卡带，但实测这些文件对 pxt 编译器是惰性的
 * （编译器只消费 .ts/.jres 等），真正决定成败的是 main.ts 有没有引用它们。
 * 所以改为放行 + 原样落盘，把判断交给编译器。
 */
function isBinaryFile(name, content) {
  const ext = path.extname(name || '').toLowerCase();
  if (BIN_EXT.has(ext)) return true;
  return looksBinary(content) !== null;
}

/*
 * 检查源码文件列表，返回有话要说的文件。
 *
 * 二进制资源（assets/xxx.png、上传的音效等）不再拦截：cartconv 会按
 * latin1 → 原始字节把它们原样写进工程，pxt 编译器对不认识的文件是惰性的。
 * 只有内容已损坏（替换字符）这种无法挽回的才值得多说一句。
 */
function inspectFiles(sources) {
  const bad = [];
  for (const name of Object.keys(sources).sort()) {
    const content = sources[name];
    const ext = path.extname(name).toLowerCase();

    if (BIN_EXT.has(ext)) {
      bad.push({
        name,
        why: '二进制资源文件（将按原样写入工程，游戏能否用到它取决于源码引用）',
        soft: true,
      });
      continue;
    }
    const bin = looksBinary(content);
    if (bin === '含非法 UTF-8 序列') {
      // 数据在制作卡带时就已损坏，写出来也是坏的，提醒一句
      bad.push({ name, why: bin, soft: true });
      continue;
    }
    if (bin) {
      // 含控制字符的文件按二进制原样写，不判断、不拦
      bad.push({ name, why: `二进制内容（${bin}，将按原样写入）`, soft: true });
      continue;
    }
    if (!TEXT_EXT.has(ext) && ext !== '') {
      // 不认识的扩展名：只是提示，交给编译器决定
      bad.push({ name, why: `未知类型 ${ext}（按文本处理，可能损坏）`, soft: true });
    }
  }
  return bad;
}

/*
 * 静态核对：源码里的 assets.*`name` 引用，在工程资源（.jres）里能不能找到。
 *
 * 背景：castle 卡带黑屏排查时才发现 main.ts 引用的资产名在 images.g.jres
 * 里对不上 —— 这类卡带编译报错晦涩（TS 找不到工厂返回值）甚至能编过但
 * 运行异常。编译前对一遍名字，提前把疑点亮出来。
 *
 * 只查工程内 .jres；扩展自带的资源（资产包）查不到，所以只 warn 不拦。
 */
const ASSET_REF_RE = /assets\.(image|tile|animation|tilemap|song)\s*`([^`]*)`/g;
const ASSET_REF_PY_RE = /assets\.(image|tile|animation|tilemap|song)\s*\(\s*"""([^"]*)"""\s*\)/g;

function collectJResNames(sources) {
  const names = new Set();
  for (const name of Object.keys(sources)) {
    if (!/\.jres$/i.test(name)) continue;
    let jres;
    try {
      jres = JSON.parse(sources[name]);
    } catch (e) {
      continue;
    }
    for (const key of Object.keys(jres)) {
      if (key === '*') continue;
      names.add(key);
      names.add(key.split('.').pop()); // images.hero → hero
      const entry = jres[key];
      if (entry && typeof entry.displayName === 'string') {
        names.add(entry.displayName);
      }
    }
  }
  return names;
}

function inspectAssetRefs(sources) {
  const names = collectJResNames(sources);
  const missing = [];
  for (const name of Object.keys(sources).sort()) {
    const content = sources[name];
    const isTs = /\.ts$/i.test(name);
    const isPy = /\.py$/i.test(name);
    if (!isTs && !isPy) continue;
    const re = isTs ? ASSET_REF_RE : ASSET_REF_PY_RE;
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(content))) {
      const refName = m[2].trim();
      if (refName && !names.has(refName)) {
        missing.push({ file: name, kind: m[1], ref: refName });
      }
    }
  }
  return missing;
}

/*
 * 依赖检查。
 *
 * 官方扩展（animation / color-coded-tilemap 等）都在 pxt-common-packages/libs
 * 里，install 时从本地复制，离线可用。以 gh: / http(s) 形式声明的社区扩展
 * 必须联网下载，离线包里必然失败 —— 这种要在编译前就说清楚。
 */
function inspectDeps(pxtJson, pxtRoot) {
  const deps = (pxtJson && pxtJson.dependencies) || {};
  const remote = [];
  const unknown = [];

  const libsDir = pxtRoot ? path.join(pxtRoot, 'pxt-common-packages', 'libs') : null;

  for (const name of Object.keys(deps).sort()) {
    if (/^(gh:|gh-|github:|https?:)/i.test(name)) {
      remote.push(name);
      continue;
    }
    // 其余按官方包名处理；本地 libs 里没有的记为未知（不致命，可能是 target 内置）
    if (libsDir && fs.existsSync(libsDir) && !fs.existsSync(path.join(libsDir, name))) {
      unknown.push(name);
    }
  }
  return { remote, unknown, all: Object.keys(deps) };
}

/*
 * install 之后核对：声明的依赖是不是真的装上了。
 * 这比看 install 的退出码可靠 —— pxt 有时退出码非 0 但已装好，有时相反。
 */
function missingDeps(workDir, deps) {
  const mods = path.join(workDir, 'pxt_modules');
  let entries = [];
  try {
    entries = fs.readdirSync(mods);
  } catch (e) {
    return Object.keys(deps || {});
  }
  const missing = [];
  for (const name of Object.keys(deps || {})) {
    // gh:user/repo#tag → repo；可能被装成 repo 或 user-repo
    const short = name.split('#')[0].split('/').pop().replace(/^gh:/, '');
    const hit = entries.some(
      (e) => e === name || e === short || e.replace(/^pxt-/, '') === short.replace(/^pxt-/, '')
    );
    if (!hit) missing.push(name);
  }
  return missing;
}

/* 卡带里记录的编译版本，与本地编译器比对。只作提示，不阻塞。 */
function inspectVersion(meta, pxtRoot) {
  const tv = (meta && meta.targetVersions) || null;
  if (!tv || !tv.target) return null;

  let local = null;
  if (pxtRoot) {
    try {
      local = JSON.parse(
        fs.readFileSync(path.join(pxtRoot, 'pxt-arcade', 'package.json'), 'utf8')
      ).version;
    } catch (e) {
      local = null;
    }
  }
  if (!local) return { cart: tv.target, pxt: tv.pxt, local: null, newer: false };

  const cmp = (a, b) => {
    const pa = String(a).split('.').map(Number);
    const pb = String(b).split('.').map(Number);
    for (let i = 0; i < 3; i++) {
      const d = (pa[i] || 0) - (pb[i] || 0);
      if (d) return d;
    }
    return 0;
  };
  // 主版本更高才算"明显更新"，避免小版本差异误报
  const cartMajor = parseInt(String(tv.target).split('.')[0], 10) || 0;
  const localMajor = parseInt(String(local).split('.')[0], 10) || 0;
  return {
    cart: tv.target,
    pxt: tv.pxt,
    local,
    newer: cartMajor > localMajor,
    sameMajorNewer: cartMajor === localMajor && cmp(tv.target, local) > 0,
  };
}

/*
 * 汇总。返回 { fatal[], warn[] }：
 *   fatal —— 不编译，直接判失败（继续也没有意义）
 *   warn  —— 继续编译，但把风险说出来
 */
function run(dec, pxtRoot) {
  const fatal = [];
  const warn = [];

  for (const b of inspectFiles(dec.sources)) {
    if (b.soft) warn.push(`文件 ${b.name}: ${b.why}`);
    else fatal.push(`文件 ${b.name}: ${b.why}`);
  }

  let pxtJson = null;
  try {
    pxtJson = dec.sources['pxt.json'] ? JSON.parse(dec.sources['pxt.json']) : null;
  } catch (e) {
    fatal.push('pxt.json 不是合法 JSON，卡带已损坏');
    pxtJson = null;
  }

  if (pxtJson) {
    const d = inspectDeps(pxtJson, pxtRoot);
    if (d.remote.length) {
      fatal.push(
        `需要联网下载社区扩展：${d.remote.join(', ')}（便携包只含官方扩展，离线无法完成）`
      );
    }
  }

  const v = inspectVersion(dec.obj && dec.obj.meta, pxtRoot);
  if (v && v.newer) {
    warn.push(
      `卡带由更新的 MakeCode 制作（target ${v.cart}），本工具内置 ${v.local}，` +
        `若用到新接口会编译失败`
    );
  }

  for (const m of inspectAssetRefs(dec.sources)) {
    warn.push(
      `源码 ${m.file} 引用 assets.${m.kind}\`${m.ref}\`，工程资源里找不到；` +
        `若该资源不是来自扩展，游戏多半会编译失败或运行缺图`
    );
  }

  return { fatal, warn, deps: pxtJson ? pxtJson.dependencies || {} : {}, version: v };
}

module.exports = { run, inspectFiles, inspectAssetRefs, isBinaryFile, inspectDeps, missingDeps, inspectVersion };
