function tagToShaAsync(repopath, tag) {
            // PATCH(mca-cartconv:tagref)
            // api.github.com 的 refs 端点对未认证调用限流 60 次/小时，超限后返回
            // 403，pxt 直接报 "Got HTTP 403. Did you forget to pxt login ?"，整
            // 个 install 失败。但 codeload.github.com/zip/<ref> 本来就接受分支名
            // 和 tag 名，不需要先解析成 40 位 sha，所以解析失败就把 ref 原样返回。
            if (/^[a-f0-9]{40}$/.test(tag))
                return Promise.resolve(tag);
            const parsed = parseRepoId(repopath);
            return ghGetJsonAsync(`https://api.github.com/repos/${parsed.slug}/git/refs/tags/${tag}`)
                .then(resolveRefAsync, e => ghGetJsonAsync(`https://api.github.com/repos/${parsed.slug}/git/refs/heads/${tag}`)
                .then(resolveRefAsync))
                .catch(e => {
                    pxt.log(`mca-cartconv: ref lookup failed for ${parsed.slug}@${tag} (${e && e.message}); using ref as-is`);
                    return tag;
                });
        }
        