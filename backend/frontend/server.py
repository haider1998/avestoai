#!/usr/bin/env python3
"""
Simple HTTP server for AvestoAI Frontend
Serves static files and provides CORS support for API calls
"""

import http.server
import socketserver
import os
import sys
from urllib.parse import urlparse
import json

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler with CORS support"""
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests"""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests with proper MIME types"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Serve index.html for root path
        if path == '/':
            path = '/index.html'
        
        # Set proper content types
        if path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
        elif path.endswith('.css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
        elif path.endswith('.js'):
            self.send_response(200)
            self.send_header('Content-type', 'application/javascript; charset=utf-8')
            self.end_headers()
        else:
            super().do_GET()
            return
        
        # Serve the file
        try:
            file_path = path.lstrip('/')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {path}")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def main():
    """Main server function"""
    # Change to frontend directory
    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(frontend_dir)
    
    # Server configuration
    PORT = int(os.getenv('FRONTEND_PORT', 3000))
    HOST = os.getenv('FRONTEND_HOST', 'localhost')
    
    print("🚀 Starting AvestoAI Frontend Server")
    print(f"📁 Serving files from: {frontend_dir}")
    print(f"🌐 Server URL: http://{HOST}:{PORT}")
    print(f"🔗 Backend API: http://localhost:8080")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer((HOST, PORT), CORSHTTPRequestHandler) as httpd:
            print(f"✅ Frontend server running on http://{HOST}:{PORT}")
            print("📱 Open this URL in your browser to access AvestoAI")
            print("🛑 Press Ctrl+C to stop the server")
            print("=" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use. Try a different port:")
            print(f"   FRONTEND_PORT=3001 python server.py")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
