# Oxalis Web Editor
#
# Copyright (C) 2005-2007 Sergej Chodarev

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

import editor

class Document(object):
    """Abstract base class for documents which can be edited in Oxalis.

    Member variables:
      * project - points to project
      * path - path to the document, relative to project directry
      * url - URL, which can be used to display document preview
        (should be defined in subclasses)
      * tree_iter -- tree iter that points to document in tree model
    """

    def __init__(self, path, project):
        '''Initializes document with path and project.'''
        self.project = project
        self.path = path
        self.tree_iter = None

    def set_path(self, path):
        self._path = path
        self._set_full_path(path)

    path = property(lambda self: self._path, set_path, None,
        'Path to the document')

    def _set_full_path(self, path):
        self.full_path = os.path.join(self.project.dir, path)

    def move(self, new_path):
        """Move document to new_path."""
        old_full_path = self.full_path
        self.path = new_path
        os.rename(old_full_path, self.full_path)

    def remove(self):
        """Remove document."""
        os.remove(self.full_path)

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

    _header_re = re.compile('(\w+): ?(.*)')

    def __init__(self, path, project):
        Document.__init__(self, path, project)
        self.read_header()

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + self.path

    @property
    def source_path(self):
        """Full path to source file of page."""
        return os.path.join(self.project.files_dir, self.path)

    @staticmethod
    def create(path, project):
        """Create new page."""
        # Create empty source file
        source_path = os.path.join(project.files_dir, path)
        f = file(source_path, 'w')
        f.write('\n')
        f.close()
        # Create empty HTML file
        full_path = os.path.join(project.dir, path)
        f = file(full_path, 'w')
        f.write('\n')
        f.close()
        return Page(path, project)

    def move(self, new_path):
        old_source_path = self.source_path
        Document.move(self, new_path)
        os.renames(old_source_path, self.source_path)

    def remove(self):
        os.remove(self.source_path)
        Document.remove(self)

    def read_header(self):
        '''Reads page header and stores it in self.header'''
        self._page_file = file(self.source_path)
        self.header = {}
        for line in self._page_file:
            if line == '\n':
                break
            else:
                match = self._header_re.match(line)
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
        f = file(self.source_path, 'w')
        for (key, value) in self.header.items():
            f.write(key + ': ' + value + '\n')
        f.write('\n')
        f.write(self.text)
        f.close()

    def create_editor(self):
        return editor.PageEditor(self)

    def generate(self):
        '''Generates HTML file'''
        tpl = Template(self.header['Template'], self.project)
        # Check if source file or template was modified after HTML file
        # was generated last time
        if not os.path.exists(self.source_path) or \
           os.path.getmtime(self.full_path) > os.path.getmtime(self.source_path) or \
           os.path.getmtime(tpl.full_path) > os.path.getmtime(self.source_path):
            f = file(self.full_path, 'w')
            f.write(self.process_page())
            f.close()

    def process_page(self):
        html = markdown.markdown(self.text)
        html = smartypants.smartyPants(html)

        html = self._process_template(html)
        encoding = self._determine_encoding(html)
        return html.encode(encoding)

    def _process_template(self, content):
        if 'Template' in self.header:
            tpl_name = self.header['Template']
        else:
            tpl_name = 'default'

        tpl = Template(tpl_name, self.project)
        tags = self.header.copy()
        tags['Content'] = content
        return tpl.process_page(tags)

    _re_xml_declaration = re.compile(
        '<\?xml.*? encoding=(?P<quote>\'|")(?P<enc>.+?)(?P=quote).*?\?>')
    _re_meta = re.compile(
        '<meta \s*http-equiv="Content-Type" \
         \s*content=(?P<quote>\'|").+?;\s*charset=(?P<enc>.+?)(?P=quote).*?>',
        re.IGNORECASE)

    def _determine_encoding(self, html):
        """Determines encoding, in which HTML document should be saved"""
        match = self._re_xml_declaration.search(html)
        if match != None:
            return match.group('enc')
        else:
            match = self._re_meta.search(html)
            if match != None:
                return match.group('enc')
            else:
                return 'UTF-8'


class Style(Document):
    '''CSS style'''

    def __init__(self, path, project):
        Document.__init__(self, path, project)

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url

    @staticmethod
    def create(path, project):
        """Create new style."""
        # Create empty file
        full_path = os.path.join(project.dir, path)
        f = file(full_path, 'w')
        f.close()
        return Style(path, project)

    def create_editor(self):
        return editor.StyleEditor(self)


class Template(Document):
    '''Template for HTML pages'''

    tag_re = re.compile('\{(\w+)\}')

    def __init__(self, path, project):
        Document.__init__(self, path, project)

    def _set_full_path(self, path):
        self.full_path = os.path.join(self.project.templates_dir, path)

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + '?template=' + self.path

    @staticmethod
    def create(path, project):
        """Create new template."""
        # Create empty file
        full_path = os.path.join(project.templates_dir, path)
        f = file(full_path, 'w')
        f.close()
        return Template(path, project)

    def create_editor(self):
        return editor.TemplateEditor(self)

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

# vim:tabstop=4:expandtab
