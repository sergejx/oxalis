# Oxalis Web Editor
#
# Copyright (C) 2005-2006 Sergej Chodarev

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
import re

import markdown
import smartypants

class Document(object):
    '''Abstract base class for documents which can be edited in Oxalis

    Member variables:
      * project - points to project
      * path - path to the document, relative to project directry
      * url - URL, which can be used to display document preview
    '''

    def __init__(self, path, project):
        '''Initializes document with path and project.'''
        self.project = project
        self.path = path

    def set_path(self, path):
        self._path = path
        self._set_full_path(path)

    path = property(lambda self: self._path, set_path, None,
        'Path to the document')

    def get_url(self):
        return None
    url = property(lambda self: self.get_url())

    def _set_full_path(self, path):
        self.full_path = os.path.join(self.project.dir, path)

    def get_text(self):
        try:
            return self._text
        except AttributeError: # Lazy initialization
            self.read_text()
            return self._text
    def set_text(self, value):
        self._text = value
    text = property(get_text, set_text, None, 'Text of the document')

    def read_text(self):
        '''Read document contents from file'''
        f = file(self.full_path, 'r')
        self._text = f.read()
        f.close()

    def write(self):
        '''Write document contents to file'''
        f = file(self.full_path, 'w')
        f.write(self.text)
        f.close()


class Page(Document):
    '''HTML page'''

    header_re = re.compile('(\w+): ?(.*)')

    def __init__(self, path, project):
        Document.__init__(self, path, project)
        self.read_header()

    def get_url(self):
        return 'http://127.0.0.1:8000/' + \
            self.project.get_url_path() + self.path[:-5] + '.html'

    def get_html_path(self):
        root, ext = os.path.splitext(self.full_path)
        return root + '.html'
    html_path = property(get_html_path, None, None,
        'Path to the HTML file generated from this page')

    def read_header(self):
        '''Reads page header and stores it in self.header'''
        self._page_file = file(self.full_path)
        self.header = {}
        for line in self._page_file:
            if line == '\n':
                break
            else:
                match = self.header_re.match(line)
                if match != None:
                    self.header[match.group(1)] = match.group(2)

    def read_text(self):
        '''Reads page text and stores it in self._text'''
        self._text = ""
        # read_header has left file opened in self.page_file
        for line in self._page_file:
            self._text += line

        self._page_file.close() # We will not need it more

    def write(self):
        f = file(self.full_path, 'w')
        for (key, value) in self.header.items():
            f.write(key + ': ' + value + '\n')
        f.write('\n')
        f.write(self.text)
        f.close()

    def generate(self):
        '''Generates HTML file'''
        tpl = Template(self.header['Template'], self.project)
        # Check if source file or template was modified after HTML file
        # was generated last time
        if not os.path.exists(self.html_path) or \
           os.path.getmtime(self.full_path) > os.path.getmtime(self.html_path) or \
           os.path.getmtime(tpl.full_path) > os.path.getmtime(self.html_path):

            f = file(self.html_path, 'w')
            f.write(self.process_page())
            f.close()

    def process_page(self):
        html = markdown.markdown(self.text)
        html = smartypants.smartyPants(html)

        html = self.process_template(html)
        encoding = determine_encoding(html)
        return html.encode(encoding)

    def process_template(self, content):
        if 'Template' in self.header:
            tpl_name = self.header['Template']
        else:
            tpl_name = 'default'

        tpl = Template(tpl_name, self.project)
        tags = self.header.copy()
        tags['Content'] = content
        return tpl.process_page(tags)


class Style(Document):
    '''CSS style'''

    def __init__(self, path, project):
        Document.__init__(self, path, project)

    def get_url(self):
        return 'http://127.0.0.1:8000/' + self.project.get_url_path()


class Template(Document):
    '''Template for HTML pages'''

    tag_re = re.compile('\{(\w+)\}')

    def __init__(self, path, project):
        Document.__init__(self, path, project)

    def _set_full_path(self, path):
        self.full_path = os.path.join(self.project.dir,
            '_oxalis', 'templates', path)

    def get_url(self):
        return 'http://127.0.0.1:8000/_oxalis?template=' + self.path

    def process_page(self, tags):
        self.tags = tags
        repl = lambda match: self.replace(match, tags)
        return self.tag_re.sub(repl, self.text)

    def replace(self, match, tags):
        tag = match.group(1)
        if tag in tags:
            return tags[tag]
        else:
            return ''


re_xml_declaration = re.compile('<\?xml.*? encoding=(?P<quote>\'|")(?P<enc>.+?)(?P=quote).*?\?>')
re_meta = re.compile('<meta \s*http-equiv="Content-Type" \s*content=(?P<quote>\'|").+?;\s*charset=(?P<enc>.+?)(?P=quote).*?>', re.IGNORECASE)

def determine_encoding(html):
    '''Determines encoding, in which HTML document should be saved'''
    match = re_xml_declaration.search(html)
    if match != None:
        return match.group('enc')
    else:
        match = re_meta.search(html)
        if match != None:
            return match.group('enc')
        else:
            return 'UTF-8'



# vim:tabstop=4:expandtab
