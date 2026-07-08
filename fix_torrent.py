import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\torrent_service.mjs', encoding='utf-8') as f:
    code = f.read()

bad_block = """    client.add(magnet, (torrent) => {
        // Find the largest file (assume it's the main video)
        req.on('close', () => {"""

good_block = """    client.add(magnet, (torrent) => {
        // Find the largest file (assume it's the main video)
        const file = torrent.files.reduce((a, b) => a.length > b.length ? a : b);
        
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
        
        req.on('close', () => {"""

code = code.replace(bad_block, good_block)

with open(r'C:\Users\acer\Desktop\Security Suite\backend\torrent_service.mjs', 'w', encoding='utf-8') as f:
    f.write(code)
