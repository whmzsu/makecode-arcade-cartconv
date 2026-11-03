function downloadTextAsync(repopath, commitid, filepath) {
            const parsed = parseRepoId(repopath);
            // PATCH(mca-cartconv): raw.githubusercontent.com is unreachable from
            // some networks (TLS handshake dies with ECONNRESET). A connection
            // error rejects the promise instead of returning a bad status code,
            // so the api.github.com contents fallback below never runs. Fetch
            // the whole repo snapshot from codeload.github.com once per
            // (repo, commit) and serve every file out of memory; fall back to
            // the contents API only if the snapshot itself fails.
            return codeloadTextAsync(parsed, commitid, filepath)
                .catch(err => {
                    pxt.log(`codeload snapshot failed for ${parsed.slug}@${commitid}: ${err && err.message}`);
                    if (isPrivateRepoCache[parsed.slug])
                        return fallbackDownloadTextAsync(parsed, commitid, filepath);
                    return pxt.U.requestAsync({
                        url: "https://raw.githubusercontent.com/" + join(parsed.slug, commitid, parsed.fileName, filepath),
                        allowHttpErrors: true
                    }).then(resp => {
                        if (resp.statusCode == 200)
                            return resp.text;
                        return fallbackDownloadTextAsync(parsed, commitid, filepath);
                    });
                });
        }
        const codeloadCache = {};
        function codeloadTextAsync(parsed, commitid, filepath) {
            const key = parsed.slug + "@" + commitid;
            const snap = codeloadCache[key];
            if (snap) {
                if (!(filepath in snap))
                    return Promise.reject(new Error("not in snapshot: " + filepath));
                return Promise.resolve(snap[filepath]);
            }
            const sub = parsed.subPath ? parsed.subPath + "/" : "";
            return pxt.U.requestAsync({
                url: "https://codeload.github.com/" + parsed.slug + "/zip/" + commitid,
                responseArrayBuffer: true,
                allowHttpErrors: true
            }).then(resp => {
                if (resp.statusCode != 200)
                    throw new Error("codeload HTTP " + resp.statusCode);
                const AdmZip = require("adm-zip");
                const zip = new AdmZip(Buffer.from(resp.buffer));
                const files = {};
                for (const e of zip.getEntries()) {
                    if (e.isDirectory)
                        continue;
                    let name = e.entryName;
                    const i = name.indexOf("/");
                    if (i >= 0)
                        name = name.slice(i + 1); // strip "repo-<ref>/" top-level dir
                    if (!name)
                        continue;
                    if (sub) {
                        if (!name.startsWith(sub))
                            continue;
                        name = name.slice(sub.length);
                    }
                    files[name] = e.getData().toString("utf8");
                }
                codeloadCache[key] = files;
                if (!(filepath in files))
                    throw new Error("not in snapshot: " + filepath);
                return files[filepath];
            });
        }
        github.downloadTextAsync = downloadTextAsync;