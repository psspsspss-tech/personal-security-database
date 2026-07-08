import os

with open(r'C:\Users\acer\Desktop\Security Suite\backend\torrent_service.mjs', encoding='utf-8') as f:
    code = f.read()

# Inject uncaught exception handler
handler = """
process.on('uncaughtException', (err) => {
    if (err.message && err.message.includes("reading 'length'")) {
        console.warn('Ignored webtorrent length bug');
        return;
    }
    console.error('Uncaught Exception:', err);
});

import fs from 'fs';
import path from 'path';
const CACHE_DIR = path.join(process.cwd(), 'cache');
if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR);
}

const cachedTorrents = {};
"""

code = code.replace("const client = new WebTorrent();", "const client = new WebTorrent();\n" + handler)

# Inject Cache Endpoints
cache_endpoints = """
app.get('/cache/add', (req, res) => {
    const magnet = req.query.magnet;
    if (!magnet) return res.status(400).json({ ok: false, error: 'Missing magnet link' });
    
    if (cachedTorrents[magnet]) {
        return res.json({ ok: true, status: 'already caching' });
    }

    client.add(magnet, { path: CACHE_DIR }, (torrent) => {
        cachedTorrents[magnet] = torrent;
        console.log(`[Cache Engine] Started caching: ${torrent.name}`);
        res.json({ ok: true, name: torrent.name, infoHash: torrent.infoHash });
    });
});

app.get('/cache/list', (req, res) => {
    const list = [];
    for (const magnet in cachedTorrents) {
        const t = cachedTorrents[magnet];
        list.push({
            name: t.name,
            infoHash: t.infoHash,
            progress: t.progress,
            downloadSpeed: t.downloadSpeed,
            downloaded: t.downloaded,
            length: t.length,
            magnet: magnet
        });
    }
    res.json({ ok: true, cache: list });
});

app.get('/cache/delete', (req, res) => {
    const magnet = req.query.magnet;
    if (cachedTorrents[magnet]) {
        const t = cachedTorrents[magnet];
        try {
            client.remove(t.infoHash, { destroyStore: true });
        } catch(e) {}
        delete cachedTorrents[magnet];
        res.json({ ok: true });
    } else {
        res.json({ ok: false, error: 'Not found' });
    }
});

app.get('/cast/devices'"""

code = code.replace("app.get('/cast/devices'", cache_endpoints)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\torrent_service.mjs', 'w', encoding='utf-8') as f:
    f.write(code)
