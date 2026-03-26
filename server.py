#!/usr/bin/env python3
"""
Simple HTTP server for testing - uses only Python standard library
"""

import http.server
import socketserver
import json
from datetime import datetime

PORT = 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "status": "ok",
            "app": "Colony OS Test",
            "time": datetime.now().isoformat(),
            "path": self.path,
            "message": "Cloudflare connection successful"
        }

        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        # Suppress logs
        pass


with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"Server running at http://0.0.0.0:{PORT}")
    httpd.serve_forever()
