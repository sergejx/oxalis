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
import shutil
import subprocess
import string
from ConfigParser import RawConfigParser
import fcntl

import gtk

import util
from document import *
from config import Configuration

default_template = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{Title}</title>
  </head>
  <body>
    {Content}
  </body>
</html>'''

sitecopy_rc = '''site $name
  server $host
  username $user
  password $passwd
  local $local
  remote $remotedir
  exclude *.text
  exclude _oxalis
'''

CONFIG_DEFAULTS = {
    'url_path': "/",
}

STATE_DEFAULTS = {
    'last_document': "index.html",
    'last_document_type': 'file',
}

# Constants for column numbers
NUM_COLUMNS = 4
OBJECT_COL, NAME_COL, PATH_COL, TYPE_COL = range(NUM_COLUMNS)


def create_project(path):
    global default_template

    name = os.path.basename(path)

    oxalis_dir = os.path.join(path, '_oxalis')
    os.mkdir(oxalis_dir)

    # Write project configuration
    config = Configuration(oxalis_dir, 'config', CONFIG_DEFAULTS)
    config.set('project_format', '0.2')
    config.write()

    upload_conf = Configuration(oxalis_dir, 'upload')
    upload_conf.write()
    # Make upload configuration file readable only by owner
    # (it contains FTP password)
    os.chmod(os.path.join(oxalis_dir, 'upload.cfg'), 0600)

    files_dir = os.path.join(oxalis_dir, 'files')
    os.mkdir(files_dir)
    f = file(os.path.join(files_dir, 'index.html'), 'w')
    f.write('Title: ' + name)
    f.write('\n\n')
    f.write(name)
    f.write('\n================')
    f.close()

    templates_dir = os.path.join(oxalis_dir, 'templates')
    os.mkdir(templates_dir)

    f = file(os.path.join(templates_dir, 'default'), 'w')
    f.write(default_template)
    f.close()

    # Create sitecopy configuration file
    f = file(os.path.join(oxalis_dir, 'sitecopyrc'), 'w')
    f.close()
    os.chmod(os.path.join(oxalis_dir, 'sitecopyrc'), 0600)

    # Sitecopy storepath
    os.mkdir(os.path.join(oxalis_dir, 'sitecopy'))
    os.chmod(os.path.join(oxalis_dir, 'sitecopy'), 0700)

def dir_is_project(directory):
    '''Checks if directory contains Oxalis project

    directory - full path to directory
    Returns True if directory contains Oxalis project or False if not
    '''
    # Simply check if directory contains subdirectory _oxalis
    return os.path.isdir(os.path.join(directory, '_oxalis'))


class Project(object):
    def __init__(self, directory):
        self.directory = directory
        self.config_dir = os.path.join(self.directory, "_oxalis")
        self.files_dir = os.path.join(self.config_dir, 'files')
        self.templates_dir = os.path.join(self.config_dir, 'templates')

        self.config = Configuration(self.config_dir, 'config', CONFIG_DEFAULTS)
        self.state = Configuration(self.config_dir, 'state', STATE_DEFAULTS)
        self.upload_conf = Configuration(self.config_dir, 'upload')

        self.load_files_tree()
        self.load_templates_list()

    def get_url_path(self):
        """Return path part of project preview URL."""
        path = self.config.get('url_path').strip('/')
        if len(path) == 0:
            return path
        else:
            return path + '/'

    @property
    def url(self):
        """Preview URL of project."""
        return 'http://127.0.0.1:8000/' + self.get_url_path()

    def load_files_tree(self):
        '''Loads tree of project files

        Tree is gtk.TreeStore with columns:
         - document object
         - display name
         - path to the file, relative to project base directory
         - type
        Type can be: dir, page, style, image, file, tpl
        Tree is stored in self.files
        '''
        self.files = gtk.TreeStore(object, str, str, str)
        self.files.set_sort_func(NAME_COL, self.sort_files_store)
        self.files.set_sort_column_id(NAME_COL, gtk.SORT_ASCENDING)
        self.load_dir('')

    def load_dir(self, dirpath, parent=None):
        '''Loads directory to files tree store

        dirpath - directory to load, path relative to self.directory
        parent - gtk.TreeIter of parent directory
        '''
        if dirpath != '':  # not root directory
            obj = Directory(dirpath, self, parent)
            parent = obj.tree_iter

        for filename in os.listdir(os.path.join(self.directory, dirpath)):
            if filename != '_oxalis':
                path = os.path.join(dirpath, filename)
                full_path = os.path.join(self.directory, path)
                if os.path.isdir(full_path):
                    self.load_dir(path, parent)
                else:
                    self.load_file(filename, path, parent)

    def load_file(self, filename, path, parent):
        '''Append file to files tree store

        filename - name of the file
        path - path relative to self.directory
        parent - gtk.TreeIter of parent directory
        '''
        name, ext = os.path.splitext(filename)
        if ext == '.html':
            Page(path, self, parent)
        elif ext == '.css':
            Style(path, self, parent)
        elif filename[0] != '.':
            File(path, self, parent)

    def sort_files_store(self, model, iter1, iter2):
        '''Comparison function for sorting files tree store'''
        name1, type1 = model.get(iter1, NAME_COL, TYPE_COL)
        name2, type2 = model.get(iter2, NAME_COL, TYPE_COL)
        if type1 == 'dir' and type2 != 'dir':
            return -1
        if type1 != 'dir' and type2 == 'dir':
            return 1
        return cmp(name1, name2)

    def load_templates_list(self):
        '''Loads list of project templates

        List is stored in self.templates and has same columns as self.files
        '''
        self.templates = gtk.ListStore(object, str, str, str)

        tpl_dir = os.path.join(self.directory, '_oxalis', 'templates')
        for filename in os.listdir(tpl_dir):
            name = os.path.basename(filename)
            Template(name, self)

    def close(self):
        """Close project and save its state"""
        self.state.write()

    def get_file_type(self, filename):
        '''Get file type from filename'''
        root, ext = os.path.splitext(filename)
        if ext == '.html':
            return 'page'
        elif ext == '.css':
            return 'style'
        elif ext in ('.png', '.jpeg', '.jpg', '.gif'):
            return 'image'

    def get_document(self, path, template=False):
        """Get document identified by path.

        Function searches specified path in files or templates tree model.
        """

        def find_document(model, tree_path, itr, data):
            path, obj = model.get(itr, PATH_COL, OBJECT_COL)
            if path == data['path']:
                data['document'] = obj
                return True
            else:
                return False

        if template:
            model = self.templates
        else:
            model = self.files
        data = {'path': path, 'document': None}
        # data['document'] is used for returning found object
        model.foreach(find_document, data)
        return data['document']

    def find_parent_dir(self, treeiter, position=gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
        '''Find parent directory of file associated with treeiter.

        If treeiter points to directory, it will be returned.
        position is for usage with Drag and Drop.
        Returns tuple of 2 items: tree iter and path to directory
        '''

        if treeiter == None:
            dir_path = ''
        else:
            type = self.files.get_value(treeiter, TYPE_COL)
            if (position == gtk.TREE_VIEW_DROP_BEFORE or
                position == gtk.TREE_VIEW_DROP_AFTER or
                type != 'dir'):
                treeiter = self.files.iter_parent(treeiter)
            if treeiter != None:
                dir_path = self.files.get_value(treeiter, PATH_COL)
            else:
                dir_path = ''
        return treeiter, dir_path

    def new_page(self, name, selected):
        '''Create new page

        name - name of page, must ends with .html
        '''
        parent, dir_path = self.find_parent_dir(selected)
        path = os.path.join(dir_path, name)
        Page(path, self, parent, True)

    def new_style(self, name, selected):
        '''Create new CSS style'''
        parent, dir_path = self.find_parent_dir(selected)
        path = os.path.join(dir_path, name)
        Style(path, self, parent, True)

    def new_dir(self, name, selected):
        '''Create new directory'''
        parent, dir_path = self.find_parent_dir(selected)
        path = os.path.join(dir_path, name)
        Directory(path, self, parent, True)

    def new_template(self, name):
        '''Create new template'''
        Template(name, self, True)

    def add_file(self, filename, selected, position=gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
        '''Add existing file to project'''
        parent, dir_path = self.find_parent_dir(selected, position)
        name = os.path.basename(filename)
        path = os.path.join(dir_path, name)
        File.add_to_project(path, self, parent, filename)

    def move_file(self, file_path, tree_path, position):
        '''Move file (used with drag&drop)

        file_path - relative path to the file
        tree_path - gtk.TreeStore path, where file was dropped
        position - position, where file was dropped
        Returns new file path if file was moved or None if not
        Caller should remove old item from tree store if move was successful
        '''
        itr = self.files.get_iter(tree_path)
        itr, dir_path = self.find_parent_dir(itr, position)
        file_dir, file_name = os.path.split(file_path)
        if file_dir == dir_path:
            return None  # File was dropped to the same directory
        else:
            obj = self.get_document(file_path)
            if itr is not None:
                dest = self.files.get_value(itr, OBJECT_COL)
            else:
                dest = Document("", self)
            obj.move(dest)

    def generate(self):
        '''Generate project output files'''
        self.files.foreach(self.generate_item)

    def generate_item(self, model, path, iter):
        obj, tp = model.get_value(iter, OBJECT_COL, TYPE_COL)
        if tp == 'page':
            obj.generate()

    def upload(self):
        '''Starts uploading of project files to server.

        Returns True of uploading was started, or False if uploading was not
        configured.
        Process of uploading can be monitored using check_upload function.
        '''
        for key in ('host', 'remotedir', 'user', 'passwd'):
            if not self.upload_conf.has_option(key):
                return False

        rcfile = os.path.join(self.config_dir, "sitecopyrc")
        storepath = os.path.join(self.config_dir, "sitecopy")

        # Check if we need to initialize sitecopy
        # It is needed if we upload to given location for the first time
        need_init = False
        for key in ('host', 'remotedir'):
            if self.upload_conf.has_option('last_'+key):
                last = self.upload_conf.get('last_'+key)
                current = self.upload_conf.get(key)
                if current != last:
                    need_init = True
        if not os.path.exists(os.path.join(storepath, 'project')):
            need_init = True

        # Update sitecopyrc file
        f = file(rcfile, 'w')
        tpl = string.Template(sitecopy_rc)
        f.write(tpl.substitute(dict(self.upload_conf.items()),
            name='project', local=self.directory))
        f.close()

        if need_init:
            sitecopy = subprocess.Popen(('sitecopy',
                '--rcfile='+rcfile, '--storepath='+storepath, '--init', 'project'))
            code = sitecopy.wait()
        self.sitecopy = subprocess.Popen(('sitecopy',
            '--rcfile='+rcfile, '--storepath='+storepath, '--update', 'project'),
            stdout=subprocess.PIPE)

        for key in ('host', 'remotedir'):
            self.upload_conf.set('last_'+key, self.upload_conf.get(key))

        return True

    def check_upload(self):
        '''Checks if upload is completed

        Returns tuple:
          - return code, or None if upload is not completed
          - string containing output of the sitecopy
        '''
        returncode = self.sitecopy.poll()
        output = ''

        # Set up asynchronous reading of sitecopy output
        fd = self.sitecopy.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        try:
            output = self.sitecopy.stdout.read()
        finally:
            return returncode, output

    def properties_dialog(self, parent_window):
        '''Display project properties dialog.'''
        settings = {}
        settings['upload'] = dict(self.upload_conf.items())
        settings['preview'] = dict(self.config.items())
        dialog = ProjectPropertiesDialog(parent_window, settings)
        response = dialog.run()
        settings = dialog.get_settings()
        dialog.destroy()

        if response == gtk.RESPONSE_OK:
            self.config.set('url_path', settings['preview']['url_path'])
            self.upload_conf.set('host', settings['upload']['host'])
            self.upload_conf.set('user', settings['upload']['user'])
            self.upload_conf.set('passwd', settings['upload']['passwd'])
            self.upload_conf.set('remotedir', settings['upload']['remotedir'])
            # Save properties
            self.config.write()
            self.upload_conf.write()


class ProjectPropertiesDialog(gtk.Dialog):
    keys = ('host', 'user', 'passwd', 'remotedir')
    texts = {'host':'Host:',
        'user':'User:',
        'passwd':'Password:',
        'remotedir':'Remote Directory:'}

    def __init__(self, window = None, settings = {}):
        gtk.Dialog.__init__(self, 'Project Properties', window,
            flags=gtk.DIALOG_NO_SEPARATOR,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_OK)

        # Upload settings
        self.entries = {}
        table_rows = []
        for key in self.keys:
            self.entries[key] = gtk.Entry()
            if key in settings['upload']:
                self.entries[key].set_text(settings['upload'][key])
            table_rows.append((self.texts[key], self.entries[key]))
        self.entries['passwd'].set_visibility(False)

        table = util.make_table(table_rows)
        table.set_row_spacings(6)
        table.set_col_spacings(12)

        # Preview settings
        vbox = gtk.VBox()
        vbox.set_spacing(6)

        hbox = gtk.HBox()
        hbox.set_spacing(12)
        hbox.pack_start(gtk.Label('Path in URL:'), False)
        self.path_entry = gtk.Entry()
        self.path_entry.set_text(settings['preview']['url_path'])
        hbox.pack_start(self.path_entry)
        vbox.pack_start(hbox)
        description = gtk.Label()
        description.set_markup(
            '<small>This setting is used for resolving absolute paths in previews. '
            'For example if your site will be accessible via adress '
            '<tt>http://www.example.com/mysite/</tt> enter <tt>mysite</tt></small>')
        description.set_line_wrap(True)
        description.set_alignment(0, 0.5)
        vbox.pack_start(description)

        # Pack everything
        box = util.make_dialog_layout((
            ('Upload settings', table),
            ('Preview settings', vbox)
        ))

        self.vbox.pack_start(box)
        self.vbox.show_all()

    def get_settings(self):
        settings = {}
        settings['upload'] = {}
        for key in self.keys:
            settings['upload'][key] = self.entries[key].get_text()
        settings['preview'] = {}
        settings['preview']['url_path'] = self.path_entry.get_text()
        return settings

# vim:tabstop=4:expandtab
