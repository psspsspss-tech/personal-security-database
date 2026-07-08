import express from 'express';
import WebTorrent from 'webtorrent';
import cors from 'cors';
import dlnacasts from 'dlnacasts';
import chromecasts from 'chromecasts';

const app = express();
const client = new WebTorrent({
    maxConns: 500,
    uploadLimit: -1,
    downloadLimit: -1
});

process.on('uncaughtException', (err) => {
    if (err.message && err.message.includes("reading 'length'")) {
        console.warn('Ignored webtorrent length bug');
        return;
    }
    if (err.message && err.message.includes("reading 'missing'")) {
        console.warn('Ignored webtorrent missing bug');
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


const dlna = dlnacasts();
const chromecastClient = chromecasts();

app.use(cors());

// Keep track of torrent metadata
const activeTorrents = {};
let dlnaDevices = {};
let castDevices = {};

dlna.on('update', (player) => {
    dlnaDevices[player.name] = player;
});

chromecastClient.on('update', (player) => {
    castDevices[player.name] = player;
});


app.get('/cache/add', (req, res) => {
    const magnet = req.query.magnet;
    const customPath = req.query.path || CACHE_DIR;
    
    if (!magnet) return res.json({ ok: false, error: 'No magnet provided' });
    if (cachedTorrents[magnet]) {
        return res.json({ ok: true, message: 'Already cached' });
    }

    if (customPath !== CACHE_DIR) {
        if (!fs.existsSync(customPath)) {
            try { fs.mkdirSync(customPath, { recursive: true }); } catch(e) {}
        }
    }

    try {
        console.log(`[Cache Engine] Queueing magnet link...`);
        const torrent = client.add(magnet, { path: customPath });
        cachedTorrents[magnet] = torrent;

        torrent.on('metadata', () => {
            console.log(`[Cache Engine] Metadata resolved for: ${torrent.name}`);
        });

        torrent.on('error', (err) => {
            console.error(`[Cache Engine] Torrent error: ${err.message}`);
        });

        res.json({ ok: true, name: 'Fetching metadata...', infoHash: torrent.infoHash });
    } catch (e) {
        console.error('[Cache Engine] client.add failed:', e);
        res.json({ ok: false, error: e.message });
    }
});

app.get('/cache/list', (req, res) => {
    const list = [];
    for (const magnet in cachedTorrents) {
        try {
            const t = cachedTorrents[magnet];
            if (!t) continue;
            let length = 0;
            try { length = t.length || 0; } catch(e) {}
            let progress = 0;
            try { progress = t.progress || 0; } catch(e) {}
            let downloadSpeed = 0;
            try { downloadSpeed = t.downloadSpeed || 0; } catch(e) {}
            let downloaded = 0;
            try { downloaded = t.downloaded || 0; } catch(e) {}
            let name = 'Fetching metadata...';
            try { name = t.name || 'Fetching metadata...'; } catch(e) {}
            
            list.push({
                name: name,
                infoHash: t.infoHash || '',
                progress: progress,
                downloadSpeed: downloadSpeed,
                downloaded: downloaded,
                length: length,
                magnet: magnet
            });
        } catch(e) {
            console.error('Error generating cache info for torrent:', e);
        }
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

app.get('/cast/devices', (req, res) => {
    const devices = [];
    for (const name in dlnaDevices) devices.push({ id: name, name, type: 'dlna' });
    for (const name in castDevices) devices.push({ id: name, name, type: 'chromecast' });
    res.json({ ok: true, devices });
});

app.get('/cast/play', (req, res) => {
    const { deviceId, type, streamUrl, title } = req.query;
    if (!deviceId || !streamUrl) return res.status(400).json({ ok: false, error: 'Missing parameters' });
    
    const player = type === 'dlna' ? dlnaDevices[deviceId] : castDevices[deviceId];
    if (player) {
        player.play(streamUrl, { title: title || 'P2P Stream' }, (err) => {
            if (err) return res.json({ ok: false, error: err.message });
            res.json({ ok: true });
        });
    } else {
        res.json({ ok: false, error: 'Device not found' });
    }
});

app.get('/stream', (req, res) => {
    let magnet = req.query.magnet;
    if (!magnet) {
        return res.status(400).json({ ok: false, error: 'Missing magnet link' });
    }

    const defaultTrackers = [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://9.rarbg.com:2810/announce',
        'udp://tracker.openbittorrent.com:6969/announce',
        'udp://exodus.desync.com:6969/announce',
        'http://tracker.openbittorrent.com:80/announce'
    ];

    defaultTrackers.forEach(tr => {
        if (!magnet.includes(encodeURIComponent(tr)) && !magnet.includes(tr)) {
            magnet += `&tr=${encodeURIComponent(tr)}`;
        }
    });

    console.log('[Torrent Service] Received magnet:', magnet.substring(0, 50) + '...');

    client.add(magnet, (torrent) => {
        // Find the largest file (assume it's the main video)
        const file = torrent.files.reduce((a, b) => a.length > b.length ? a : b);
        file.select(); // Prioritize this file for stream
        
        if (!activeTorrents[magnet]) {
            activeTorrents[magnet] = 0;
        }
        activeTorrents[magnet]++;
        activeTorrents[torrent.infoHash] = file;
        
        console.log(`[Torrent Service] Ready: ${file.name}`);
        res.json({ 
            ok: true, 
            path: `/play/${torrent.infoHash}`, 
            title: `[P2P] ${file.name}` 
        });
        
        req.on('close', () => {
            if (activeTorrents[magnet]) {
                activeTorrents[magnet]--;
                if (activeTorrents[magnet] === 0) {
                    console.log(`[Torrent Service] Closing torrent: ${torrent.name}`);
                    try {
                        client.remove(torrent.infoHash, { destroyStore: true });
                    } catch (e) {
                        console.error('Error removing torrent:', e);
                    }
                    delete activeTorrents[magnet];
                }
            }
        });
    });
});

app.get('/play/:infoHash', (req, res) => {
    const file = activeTorrents[req.params.infoHash];
    if (!file) {
        return res.status(404).send('Torrent not found or expired');
    }

    const range = req.headers.range;
    if (!range) {
        res.writeHead(200, {
            'Content-Length': file.length,
            'Content-Type': 'video/mp4'
        });
        file.createReadStream().pipe(res);
        return;
    }

    const positions = range.replace(/bytes=/, "").split("-");
    const start = parseInt(positions[0], 10);
    const end = positions[1] ? parseInt(positions[1], 10) : file.length - 1;
    const chunksize = (end - start) + 1;

    res.writeHead(206, {
        'Content-Range': `bytes ${start}-${end}/${file.length}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': chunksize,
        'Content-Type': 'video/mp4'
    });

    const stream = file.createReadStream({ start, end });
    
    stream.on('error', (err) => {
        // Ignore stream premature close errors
    });
    res.on('error', () => {
        stream.destroy();
    });
    res.on('close', () => {
        stream.destroy();
    });
    
    stream.pipe(res);
});

app.listen(8766, '0.0.0.0', () => {
    console.log('[Torrent Service] Microservice running on port 8766');
});
