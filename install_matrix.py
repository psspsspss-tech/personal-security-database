import re

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', encoding='utf-8') as f:
    py = f.read()

if "import imageio_ffmpeg" not in py:
    py = py.replace("import subprocess", "import subprocess\nimport imageio_ffmpeg")

routes = """
@app.route('/api/media/transcode/live')
def transcode_live():
    url = request.args.get('url')
    ss = request.args.get('ss', '0')
    if not url:
        return jsonify({"ok": False, "error": "Missing URL"}), 400

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, 
            '-ss', str(ss),
            '-i', url,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', 'frag_keyframe+empty_moov+faststart',
            '-f', 'mp4',
            'pipe:1'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return Response(process.stdout, mimetype='video/mp4')
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/radar/scan')
def radar_scan():
    import platform
    devices = []
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output("arp -a", shell=True).decode(errors='ignore')
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0].count('.') == 3 and parts[1].count('-') == 5:
                    devices.append({"ip": parts[0], "mac": parts[1], "type": parts[2] if len(parts) > 2 else "unknown"})
        
        # Deduplicate
        seen = set()
        unique = []
        for d in devices:
            if d['ip'] not in seen:
                seen.add(d['ip'])
                unique.append(d)
                
        return jsonify({"ok": True, "devices": unique})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
"""

py = py.replace("@app.route('/api/media/extract', methods=['POST'])", routes + "\n@app.route('/api/media/extract', methods=['POST'])")

with open(r'C:\Users\acer\Desktop\Security Suite\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(py)
