import http.server
import socketserver
import os

PORT = 8064

class PlainTextHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/MainScript/Source':
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            try:
                # Make sure your Source.txt is in the same directory as this script
                with open('Source.txt', 'r') as file:
                    self.wfile.write(file.read().encode())
            except FileNotFoundError:
                self.send_error(404, "File Not Found")
        else:
            self.send_error(404, "Endpoint Not Found")

# Bind to localhost and the specified port
with socketserver.TCPServer(("localhost", PORT), PlainTextHandler) as httpd:
    print(f"Serving on http://localhost:{PORT}")
    httpd.serve_forever()
