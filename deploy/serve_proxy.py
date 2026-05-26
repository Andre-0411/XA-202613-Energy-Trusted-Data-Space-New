import http.server
import socketserver
import os
import http.client

DIST_DIR = r"D:\EnergyTDS\frontend\dist"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

os.chdir(DIST_DIR)

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def end_headers(self):
        if self.path.endswith('.html') or self.path == '/':
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        elif self.path.endswith('.js') or self.path.endswith('.css'):
            self.send_header('Cache-Control', 'public, max-age=0, must-revalidate')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/") or self.path.startswith("/ws/"):
            return self._proxy_request("GET")
        file_path = self.translate_path(self.path)
        if os.path.isfile(file_path):
            return super().do_GET()
        self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") or self.path.startswith("/ws/"):
            return self._proxy_request("POST")
        self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/") or self.path.startswith("/ws/"):
            return self._proxy_request("PUT")
        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/") or self.path.startswith("/ws/"):
            return self._proxy_request("DELETE")
        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _proxy_request(self, method):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        headers = {}
        for key in ["Content-Type", "Authorization", "Accept", "Origin"]:
            val = self.headers.get(key)
            if val:
                headers[key] = val
        try:
            conn = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=30)
            conn.request(method, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                if key.lower() not in ("transfer-encoding", "connection", "keep-alive"):
                    self.send_header(key, val)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(('{"error": "%s"}' % str(e)).encode())

PORT = 3000
with socketserver.TCPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
    print("Serving on port %d" % PORT)
    httpd.serve_forever()
