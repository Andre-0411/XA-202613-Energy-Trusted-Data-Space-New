import http.server
import socketserver
import os
import http.client
import socket
import select

DIST_DIR = r"D:\EnergyTDS\frontend\dist"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000

os.chdir(DIST_DIR)


class WebSocketProxy:
    """WebSocket代理 - 直接转发后端的握手响应"""
    
    @staticmethod
    def handle(client_handler, path):
        """处理WebSocket连接"""
        client_key = client_handler.headers.get('Sec-WebSocket-Key', '')
        client_version = client_handler.headers.get('Sec-WebSocket-Version', '13')
        
        # 连接后端
        try:
            backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_sock.settimeout(120)
            backend_sock.connect((BACKEND_HOST, BACKEND_PORT))
        except Exception as e:
            client_handler.send_error(502, f"Backend connection failed: {e}")
            return
        
        # 构建握手请求
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {BACKEND_HOST}:{BACKEND_PORT}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {client_key}\r\n"
            f"Sec-WebSocket-Version: {client_version}\r\n"
        )
        
        # 转发头
        for header in ['Origin', 'Sec-WebSocket-Protocol', 'Sec-WebSocket-Extensions', 'Authorization']:
            val = client_handler.headers.get(header)
            if val:
                handshake += f"{header}: {val}\r\n"
        
        handshake += "\r\n"
        
        try:
            backend_sock.sendall(handshake.encode())
        except Exception as e:
            client_handler.send_error(502, f"Handshake send failed: {e}")
            backend_sock.close()
            return
        
        # 读取后端响应
        try:
            backend_response = b""
            while b"\r\n\r\n" not in backend_response:
                chunk = backend_sock.recv(4096)
                if not chunk:
                    break
                backend_response += chunk
        except Exception as e:
            client_handler.send_error(502, f"Handshake read failed: {e}")
            backend_sock.close()
            return
        
        # 检查101
        if b"101" not in backend_response.split(b"\r\n")[0]:
            client_handler.wfile.write(backend_response)
            backend_sock.close()
            return
        
        # 直接转发后端的101响应给客户端（保留原始的Sec-WebSocket-Accept）
        try:
            client_handler.wfile.write(backend_response)
            client_handler.wfile.flush()
        except:
            backend_sock.close()
            return
        
        # 双向转发
        WebSocketProxy._proxy_loop(client_handler.connection, backend_sock)
    
    @staticmethod
    def _proxy_loop(client_sock, backend_sock):
        sockets = [client_sock, backend_sock]
        try:
            while True:
                readable, _, exceptional = select.select(sockets, [], sockets, 120)
                if exceptional:
                    break
                if not readable:
                    # 超时，发送ping
                    try:
                        backend_sock.sendall(b'\x89\x80\x00\x00\x00\x00')
                    except:
                        break
                    continue
                for sock in readable:
                    try:
                        data = sock.recv(65536)
                        if not data:
                            return
                        target = backend_sock if sock is client_sock else client_sock
                        target.sendall(data)
                    except:
                        return
        except:
            pass
        finally:
            try: client_sock.close()
            except: pass
            try: backend_sock.close()
            except: pass


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
        # WebSocket检测 - 检查路径和Upgrade头
        if self.path.startswith("/ws/"):
            upgrade = self.headers.get('Upgrade', '').lower()
            connection = self.headers.get('Connection', '').lower()
            if upgrade == 'websocket' or 'upgrade' in connection:
                return WebSocketProxy.handle(self, self.path)
        
        if self.path.startswith("/api/") or self.path.startswith("/ws/"):
            return self._proxy_request("GET")
        
        file_path = self.translate_path(self.path)
        if os.path.isfile(file_path):
            return super().do_GET()
        self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy_request("POST")
        self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self._proxy_request("PUT")
        self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self._proxy_request("DELETE")
        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Upgrade, Connection, Sec-WebSocket-Key, Sec-WebSocket-Version, Sec-WebSocket-Protocol")
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

    def log_message(self, format, *args):
        if args and len(args) > 0:
            status = str(args[1]) if len(args) > 1 else ""
            if "404" in status or "500" in status or "502" in status:
                super().log_message(format, *args)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True
    allow_reuse_port = True


PORT = 3000
with ReusableTCPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
    print(f"Serving on port {PORT} with WebSocket support")
    httpd.serve_forever()
