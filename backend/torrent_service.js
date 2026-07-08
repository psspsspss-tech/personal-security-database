const express = require('express');
const WebTorrent = require('webtorrent');
const cors = require('cors');

const app = express();
const client = new WebTorrent();

app.use(cors());

// Keep track of torrent metadata
const activeTorrents = {};

app.get('/stream', (req, res) => {
    const magnet = req.query.magnet;
    if (!magnet) {
        return res.status(400).json({ ok: false, error: 'Missing magnet link' });
    }

    console.log('[Torrent Service] Received magnet:', magnet.substring(0, 50) + '...');

    client.add(magnet, (torrent) => {
        // Find the largest file (assume it's the main video)
        const file = torrent.files.reduce((a, b) => a.length > b.length ? a : b);
        
        activeTorrents[torrent.infoHash] = file;
        
        console.log('[Torrent Service] Ready:', file.name);
        res.json({ 
            ok: true, 
            path: `/play/${torrent.infoHash}`, 
            title: `[P2P] ${file.name}` 
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

    file.createReadStream({ start, end }).pipe(res);
});

app.listen(8766, '0.0.0.0', () => {
    console.log('[Torrent Service] Microservice running on port 8766');
});
