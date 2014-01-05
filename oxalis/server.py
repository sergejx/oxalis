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
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import shutil

from generator import process_page, fill_template
from site import Page

# Global variables
site = None

page_for_templates = {
    'Title': 'Lorem Ipsum',
    'Content': '''
<p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Donec suscipit, odio vitae consequat tristique, neque urna semper libero, eget volutpat augue diam sit amet magna. Phasellus fermentum, tortor non dapibus nonummy, pede orci suscipit lacus, id pharetra est magna eu lorem. Aenean ultrices iaculis dui. Integer dapibus hendrerit erat. Nam iaculis mollis enim. Nam rutrum vestibulum velit. Nulla non magna. Nunc arcu. Mauris at pede. Curabitur ligula urna, bibendum quis, vestibulum nec, cursus a, sapien.</p>

<p>Praesent tincidunt massa ac dui. Maecenas euismod, urna at pharetra molestie, mauris nisi dapibus lacus, eu mollis mi ante eget eros. Etiam iaculis sapien. Praesent eget ante vulputate dui laoreet hendrerit. Vestibulum euismod. Nam tristique laoreet est. Vivamus malesuada diam eget nunc. Proin ut nisl eu justo laoreet accumsan. Nunc ac augue. Sed laoreet libero sed dolor. Vestibulum laoreet consectetuer tellus. Pellentesque gravida tortor sit amet leo. Praesent et tortor ac ante scelerisque venenatis. Suspendisse ultricies, magna vitae feugiat facilisis, diam est scelerisque nisl, nec placerat enim odio sed leo. Cras et pede. In sed metus. In vitae dolor. Duis sed elit.</p>

<p>Donec metus lectus, pharetra id, dictum vel, iaculis condimentum, dolor. Fusce arcu. Nam justo justo, porta nec, scelerisque sit amet, pretium at, magna. Integer in augue non purus placerat condimentum. Praesent facilisis nisi ac mauris. Aliquam cursus volutpat ipsum. Donec tincidunt risus vel tellus. Nullam blandit orci in dolor. Proin est. Nunc sed nisi. Maecenas quis turpis id mi dapibus mattis. Etiam mollis libero eu ligula. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus.</p>

<p>Mauris rutrum arcu vel augue. Aliquam pellentesque augue ut nunc. Praesent gravida lectus nec nulla. Nunc suscipit sapien at tellus. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Quisque ut ligula. In hac habitasse platea dictumst. Fusce aliquet risus a nibh. In vitae massa. Morbi sit amet libero nec quam iaculis semper. Sed id velit. Etiam porttitor. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Curabitur eu sapien nec lacus posuere nonummy. Nunc tincidunt.</p>
'''}



def run():
    '''Run the server'''
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, OxalisHTTPRequestHandler)
    httpd.serve_forever()

class OxalisHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_index = self.path.find('?')
        if query_index != -1:
            query = self.path[query_index+1:]
            param = query.split('=')
            if param[0] == 'template':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()

                tpl = site.get_document(param[1], True)
                html = fill_template(tpl, page_for_templates)
                self.wfile.write(html)
            else:
                self.send_error(404, 'Not Found')
        else:
            base_path = site.get_url_path()
            request_path = self.path[1:]
            request_path = request_path[len(base_path):]
            full_path = os.path.join(site.directory, request_path)
            if os.path.isdir(full_path):
                request_path = os.path.join(request_path, 'index.html')
                full_path = os.path.join(full_path, 'index.html')
            root, ext = os.path.splitext(request_path)

            if ext == '.html':  # Pages
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()

                page = site.get_document(request_path)
                # FIXME: This logic should not be here
                if isinstance(page, Page):
                    html = process_page(page)
                else:
                    html = page.read()
                self.wfile.write(html)

            elif os.path.exists(full_path):  # Other files
                mime = mimetypes.guess_type(full_path)

                self.send_response(200)
                self.send_header('Content-Type', mime[0])
                self.end_headers()

                f = file(full_path, 'r')
                shutil.copyfileobj(f, self.wfile)
                f.close()

            else:  # File not found
                self.send_error(404, 'Not Found')
