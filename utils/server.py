import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import threading

def get_free_port():
    """Find a free port on localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    addr, port = s.getsockname()
    s.close()
    return port


class TileHTTPServer(threading.Thread):
    """Threaded HTTP server serving a specific folder."""
    def __init__(self, folder_path, port):
        super().__init__(daemon=True)
        self.folder_path = folder_path
        self.port = port
        self.httpd = None

    def run(self):
        os.chdir(self.folder_path)
        handler = SimpleHTTPRequestHandler
        self.httpd = ThreadingHTTPServer(("localhost", self.port), handler)
        print(f"Serving tiles from {self.folder_path} at http://localhost:{self.port}")
        self.httpd.serve_forever()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()