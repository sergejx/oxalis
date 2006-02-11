# Oxalis Web Site Editor
#
# This module contains small web server integrated in Oxalis and used for
# previews
#
# Copyright (C) 2006 Sergej Chodarev

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
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import shutil

from project import Page

# Global variables
project = None


def run():
	'''Run the server'''
	server_address = ('127.0.0.1', 8000)
	httpd = HTTPServer(server_address, OxalisHTTPRequestHandler)
	httpd.serve_forever()

class OxalisHTTPRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		path = os.path.join(project.dir, self.path[1:])
		if os.path.isdir(path):
			path = os.path.join(path, 'index.html')
		root, ext = os.path.splitext(path)
		
		if ext == '.html':  # Pages
			path = root + '.text'
			
			self.send_response(200)
			self.send_header('Content-Type', 'text/html')
			self.end_headers()
			
			page = Page(project, path)
			html = page.process_page()
			self.wfile.write(html)
		
		elif os.path.exists(path):  # Other files
			mime = mimetypes.guess_type(path)
			
			self.send_response(200)
			self.send_header('Content-Type', mime)
			self.end_headers()
			
			f = file(path, 'r')
			shutil.copyfileobj(f, self.wfile)
			f.close()
		
		else:  # File not found
			self.send_response(404)
