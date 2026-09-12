import os, functools, http.server, socketserver
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
http.server.SimpleHTTPRequestHandler.extensions_map.setdefault(".webp", "image/webp")
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 4173), Handler) as httpd:
    print(f"serving {ROOT} on http://127.0.0.1:4173", flush=True)
    httpd.serve_forever()
