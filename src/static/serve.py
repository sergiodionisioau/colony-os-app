#!/usr/bin/env python3
import http.server
import socketserver
import os
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
    print(f"Serving at http://0.0.0.0:{port}")
    httpd.serve_forever()
