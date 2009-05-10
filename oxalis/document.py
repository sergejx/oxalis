# Oxalis Web Editor
#
# Copyright (C) 2005-2009 Sergej Chodarev

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
import shutil

import markdown
import smartypants

import project
import editor

class NoEditorException(Exception):
    """Exception raised if no editor can be created for document."""
    pass

class Document(object):
    """
    Abstract base class for documents which can be part of Oxalis project.

    Member variables:
      - path -- path to the document, relative to project directory
      - project -- points to project
      - tree_iter -- tree iter pointing to document in tree model
      - model -- tree model in which document is stored
                 (default -- project.files)

    Properties:
      - full_path -- full path to the document file
      - name -- file name of document
      - url -- URL, which can be used to display document preview
        (should be defined in subclasses)
      - parent -- parent document

    Methods:
      - move(destination) -- move document to different directory
      - update_path() -- update document path based on parent path
      - rename(new_name)
      - remove()
      - create_editor() -- create editor for document
    """

    def __init__(self, path, project):
        """
        Initialize document with path and project.

        Constructors of subclasses typically have these additional arguments:
          - parent -- tree iter of parent directory
          - create -- if create == True, constructor will create new document
                      on disk
        """
        self.project = project
        self.path = path
        self.tree_iter = None
        self.model = project.files

    @property
    def full_path(self):
        """Full path to document file."""
        return os.path.join(self.project.directory, self.path)

    @property
    def name(self):
        """File name of document."""
        return os.path.basename(self.path)

    @property
    def parent(self):
        """
        Parent document.

        If document has no parent, special Document object is used with path
        set to "".
        """
        parent_itr = self.model.iter_parent(self.tree_iter)
        if parent_itr is not None:
            parent = self.model.get_value(parent_itr, project.OBJECT_COL)
        else:
            # Dummy document representing tree root
            parent = Document("", self.project)
        return parent

    def _move_files(self, new_path):
        """Move document files to new_path."""
        old_full_path = self.full_path
        self.path = new_path
        os.rename(old_full_path, self.full_path)

    def _move_tree_row(self, destination):
        """
        Move document tree row to new location.

        destination -- new parent document
        """
        row_data = self.model.get(self.tree_iter,
            *range(project.NUM_COLUMNS))
        new_iter = self.model.append(destination.tree_iter, row_data)
        self.model.remove(self.tree_iter)
        self.tree_iter = new_iter

    def move(self, destination):
        """Move document to different directory.

        destination -- directory object
        """
        dest_path = os.path.join(destination.path, self.name)
        self._move_files(dest_path)
        self._move_tree_row(destination)
        return dest_path

    def update_path(self):
        """Update document path based on parent path and document name."""
        dir_path = self.parent.path
        self.path = os.path.join(dir_path, self.name)
        self.model.set(self.tree_iter, project.PATH_COL, self.path)

    def rename(self, new_name):
        """Rename document."""
        head, tail = os.path.split(self.path)
        new_path = os.path.join(head, new_name)
        self._move_files(new_path)

        self.model.set(self.tree_iter, project.NAME_COL, new_name)
        self.model.set(self.tree_iter, project.PATH_COL, new_path)
        return new_path

    def remove(self):
        """Remove document."""
        os.remove(self.full_path)
        self.model.remove(self.tree_iter)

    def create_editor(self):
        """Return new editor component for document."""
        raise NoEditorException

class Editable(Document):
    """
    Base class for editable documents.

    Contains methods for reading and modifying document text.

    Property:
      - text

    Methods:
      - read_text()
      - write()
    """

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


class Page(Editable):
    '''HTML page'''

    _header_re = re.compile('(\w+): ?(.*)')

    def __init__(self, path, project, parent, create=False):
        """Initialize page.

        * parent - gtk.TreeIter of parent directory
        * if create == True, create new page file
        """
        super(Page, self).__init__(path, project)
        if create:
            src = file(self.source_path, 'w')
            src.write('\n')
            file(self.full_path, 'w')
        self.read_header()
        self.tree_iter = self.model.append(parent, (self, self.name, path, 'page'))

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + self.path

    @property
    def source_path(self):
        """Full path to source of document."""
        root, ext = os.path.splitext(self.full_path)
        return root + ".text"

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

    def _move_files(self, new_path):
        """Move file and its source (overrides Document._move_files())."""
        old_source_path = self.source_path
        super(Page, self)._move_files(new_path)
        os.renames(old_source_path, self.source_path)

    def remove(self):
        """Remove file and its source (overrides Document.remove())."""
        os.remove(self.source_path)
        super(WithSource, self).remove()

    def create_editor(self):
        return editor.PageEditor(self)

    def generate(self):
        '''Generates HTML file'''
        tpl = self.project.get_document(self.header['Template'], True)
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

        tpl = self.project.get_document(tpl_name, True)
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


class Style(Editable):
    '''CSS style'''

    def __init__(self, path, project, parent, create=False):
        super(Style, self).__init__(path, project)
        if create:
            file(self.full_path, 'w')
        self.tree_iter = self.model.append(parent, (self, self.name, path, 'style'))

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url

    def create_editor(self):
        return editor.StyleEditor(self)


class Template(Editable):
    '''Template for HTML pages'''

    tag_re = re.compile('\{(\w+)\}')

    def __init__(self, path, project, create=False):
        super(Template, self).__init__(path, project)
        self.model = project.templates
        if create:
            file(self.full_path, 'w')
        self.tree_iter = self.model.append((self, self.name, path, 'tpl'))

    @property
    def full_path(self):
        return os.path.join(self.project.templates_dir, self.path)

    @property
    def url(self):
        """Preview URL of document"""
        return self.project.url + '?template=' + self.path

    def rename(self, new_name):
        """Rename template."""
        # TODO: Change name of template in all pages which use it
        return super(Template, self).rename(new_name)

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

class Directory(Document):
    def __init__(self, path, project, parent, create=False):
        super(Directory, self).__init__(path, project)
        if create:
            os.mkdir(self.full_path)
        self.tree_iter = self.model.append(parent, (self, self.name, path, 'dir'))

    def _move_tree_row(self, destination):
        # Move data in tree
        old_iter = self.tree_iter
        row_data = self.model.get(self.tree_iter,
            *range(project.NUM_COLUMNS))
        self.tree_iter = self.model.append(destination.tree_iter, row_data)

        # Move children
        tree_path = self.model.get_path(old_iter)
        for row in self.model[tree_path].iterchildren():
            obj = row[project.OBJECT_COL]
            obj._move_tree_row(self)

        # Remove old row
        self.model.remove(old_iter)

    def rename(self, new_name):
        super(Directory, self).rename(new_name)
        self.update_path()

    def update_path(self):
        """Update directory path based on parent path and directory name.

        Also recursively updates children documents.
        Overrides Document.update_path().
        """
        super(Directory, self).update_path()
        tree_path = self.model.get_path(self.tree_iter)
        for row in self.model[tree_path].iterchildren():
            obj = row[project.OBJECT_COL]
            obj.update_path()

    def remove(self):
        """Remove directory (overrides Document.remove())."""
        shutil.rmtree(self.full_path)
        self.model.remove(self.tree_iter)


class File(Document):
    def __init__(self, path, project, parent):
        Document.__init__(self, path, project)

        ext = os.path.splitext(path)[1]
        if ext in ('.png', '.jpeg', '.jpg', '.gif'):
            tp = 'image'
        else:
            tp = 'file'
        self.tree_iter = self.model.append(parent, (self, self.name, path, tp))

    @staticmethod
    def add_to_project(path, project, parent, filename):
        """Copy file to project"""
        full_path = os.path.join(project.directory, path)
        shutil.copyfile(filename, full_path)
        return File(path, project, parent)

# vim:tabstop=4:expandtab
