import http.server
import socketserver

PORT = 8064

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/MainScript/Source':
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'loadstring(game:HttpGet("https://raw.githubusercontent.com/SynthiaHub/Synthia/main/Protected_4839531692977703.txt"))()')
        elif self.path == '/discord':
            self.send_response(301)
            self.send_header("Location", "https://discord.com/invite/VRn8DPSa")
            self.end_headers()
        else:
            self.send_error(404, "File Not Found")

with socketserver.TCPServer(("localhost", PORT), CustomHandler) as httpd:
    print(f"Serving on http://localhost:{PORT}")
    httpd.serve_forever()
