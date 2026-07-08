with open(r'backend\server.py', encoding='utf-8') as f:
    code = f.read()

# Replace the Node.js port (8766) with Go Streamer port (8767) for the stream route
code = code.replace("127.0.0.1:8766/stream", "127.0.0.1:8767/stream")

with open(r'backend\server.py', 'w', encoding='utf-8') as f:
    f.write(code)
