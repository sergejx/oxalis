# Oxalis Web Site Editor
#
# This module contains small web server integrated in Oxalis and used for
# previews
#
# Copyright (C) 2006-2007 Sergej Chodarev

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

# Global variables
site = None

class PreviewServer:
    def __init__(self, site):
        self.site = site

    def start(self):
        global site
        site = self.site
        server_thread = Thread(target=run)
        server_thread.setDaemon(True)
        server_thread.start()


def run():
    '''Run the server'''
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, OxalisHTTPRequestHandler)
    httpd.serve_forever()

class OxalisHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
            base_path = site.get_url_path()
            request_path = self.path[1:]
            request_path = request_path[len(base_path):]
            full_path = os.path.join(site.directory, request_path)
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
