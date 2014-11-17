# Oxalis -- A website building tool for Gnome
# Copyright (C) 2006-2014 Sergej Chodarev

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import shutil
from threading import Thread


class PreviewServer:
    def __init__(self, site):
        self.site = site
        self.port = 0

    def start(self):
        server_thread = Thread(target=self.run)
        server_thread.setDaemon(True)
        server_thread.start()

    def run(self):
        try:
            server_address = ('0.0.0.0', 8000)  # Use port 8000 by default.
            httpd = HTTPServer(server_address, PreviewServer.RequestHandler)
        except OSError:                         # If port is not available,
            server_address = ('0.0.0.0', 0)     # use random free port number.
            httpd = HTTPServer(server_address, PreviewServer.RequestHandler)
        httpd.site = self.site  # Make site object available to the handler
        self.port = httpd.server_port
        httpd.serve_forever()

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
                base_path = self.server.site.get_url_path()
                request_path = self.path[1:]
                request_path = request_path[len(base_path):]
                full_path = os.path.join(self.server.site.directory, request_path)
                if os.path.isdir(full_path):
                    full_path = os.path.join(full_path, 'index.html')

                if os.path.exists(full_path):  # Other files
                    mime = mimetypes.guess_type(full_path)

                    self.send_response(200)
                    self.send_header('Content-Type', mime[0])
                    self.end_headers()

                    f = open(full_path, 'rb')
                    shutil.copyfileobj(f, self.wfile)
                    f.close()

                else:  # File not found
                    self.send_error(404, 'Not Found')
