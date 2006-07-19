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
import shutil
import subprocess
import string
import re
from ConfigParser import RawConfigParser

import gtk

import markdown
import smartypants

import util

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

def create_project(path):
	global default_template
	
	name = os.path.basename(path)
	
	oxalis_dir = os.path.join(path, '_oxalis')
	os.mkdir(oxalis_dir)
	
	# Write project configuration
	config_file = os.path.join(oxalis_dir, 'config')
	config = RawConfigParser()
	config.add_section('project')
	config.set('project', 'format', '0.1')
	config.add_section('upload')
	f = file(config_file, 'w')
	config.write(f)
	f.close()
	# Make configuration file readable only by owner (it contains FTP password)
	os.chmod(config_file, 0600)
	
	f = file(os.path.join(path, 'index.text'), 'w')
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
	def __init__(self, dir):
		self.dir = dir
		self.config = RawConfigParser()
		# Set default configuration
		self.config.add_section('state')
		self.config.set('state', 'last_file', 'index.text')
		self.config.set('state', 'last_template', 'default')
		self.config.add_section('preview')
		self.config.set('preview', 'url_path', '/')
		# Read configuration
		self.config.read(os.path.join(self.dir, '_oxalis', 'config'))
		
		self.load_files_tree()
		self.load_templates_list()
		
	def get_url_path(self):
		return self.config.get('preview', 'url_path').strip('/') + '/'
	
	def load_files_tree(self):
		'''Loads tree of project files
		
		Tree is gtk.TreeStore with columns:
		 - display name
		 - path to the file, relative to project base directory
		 - type
		Type can be: dir, page, style, image, file, tpl
		Tree is stored in self.files
		'''
		self.files = gtk.TreeStore(str, str, str)
		self.files.set_sort_func(0, self.sort_files_store)
		self.files.set_sort_column_id(0, gtk.SORT_ASCENDING)
		self.load_dir('')
	
	def load_dir(self, dirpath, parent=None):
		'''Loads directory to files tree store
		
		dirpath - directory to load, path relative to self.dir
		parent - gtk.TreeIter of parent directory
		'''
		if dirpath != '':  # not root directory
			name = os.path.basename(dirpath)
			parent = self.files.append(parent, (name, dirpath, 'dir'))
		
		for filename in os.listdir(os.path.join(self.dir, dirpath)):
			if filename != '_oxalis':
				path = os.path.join(dirpath, filename)
				full_path = os.path.join(self.dir, path)
				if os.path.isdir(full_path):
					self.load_dir(path, parent)
				else:
					self.load_file(filename, path, parent)
				
	def load_file(self, filename, path, parent):
		'''Append file to files tree store
		
		filename - name of the file
		path - path relative to self.dir
		parent - gtk.TreeIter of parent directory
		'''
		name, ext = os.path.splitext(filename)
		if ext == '.text':
			name += '.html'
			self.files.append(parent, (name, path, 'page'))
		elif ext == '.css':
			self.files.append(parent, (filename, path, 'style'))
		elif ext in ('.png', '.jpeg', '.jpg', '.gif'):
			self.files.append(parent, (filename, path, 'image'))
		elif ext != '.html' and filename[0] != '.':
			self.files.append(parent, (filename, path, 'file'))
	
	def sort_files_store(self, model, iter1, iter2):
		'''Comparison function for sorting files tree store'''
		name1, type1 = model.get(iter1, 0, 2)
		name2, type2 = model.get(iter2, 0, 2)
		if type1 == 'dir' and type2 != 'dir':
			return -1
		if type1 != 'dir' and type2 == 'dir':
			return 1
		return cmp(name1, name2)
	
	def load_templates_list(self):
		'''Loads list of project templates
		
		List is stored in self.templates and has same columns as self.files
		'''
		self.templates = gtk.ListStore(str, str, str)
		
		tpl_dir = os.path.join(self.dir, '_oxalis', 'templates')
		for filename in os.listdir(tpl_dir):
			name = os.path.basename(filename)
			self.templates.append((name, filename, 'tpl'))
	
	def close(self, comp_file):
		'''Close project and save last opened files in both components'''
		self.config.set('state', 'last_file', comp_file['files'][0])
		self.config.set('state', 'last_template', comp_file['templates'][0])
		# Save properties
		f = file(os.path.join(self.dir, '_oxalis', 'config'), 'w')
		self.config.write(f)
		f.close
	
	def get_file_type(self, filename):
		'''Get file type from filename'''
		root, ext = os.path.splitext(filename)
		if ext == '.text':
			return 'page'
		elif ext == '.css':
			return 'style'
		elif ext in ('.png', '.jpeg', '.jpg', '.gif'):
			return 'image'
	
	def find_parent_dir(self, selected):
		'''Find parent directory for adding new file to project
		
		If directory is selected, returns it, else return parent directory of
		selected file.
		Returns tuple of 2 items: tree iter and path to directory
		'''
		if selected == None:
			parent = None
			dir = ''
		elif self.files.get_value(selected, 2) == 'dir':
			parent = selected
			dir = self.files.get_value(selected, 1)
		else:
			parent = self.files.iter_parent(selected)
			if parent != None:
				dir = self.files.get_value(parent, 1)
			else:
				dir = ''
		return parent, dir
	
	def new_page(self, name, selected):
		'''Create new page
		
		name - name of page, must ends with .html
		'''
		parent, dir = self.find_parent_dir(selected)
		path = os.path.join(dir, name)
		path = path[:-4] + 'text'  # Change extension from .html to .text
		full_path = os.path.join(self.dir, path)
		# Create empty page
		f = file(full_path, 'w')
		f.write('\n')
		f.close()
		
		self.files.append(parent, (name, path, 'page'))
	
	def new_style(self, name, selected):
		'''Create new CSS style'''
		parent, dir = self.find_parent_dir(selected)
		path = os.path.join(dir, name)
		full_path = os.path.join(self.dir, path)
		# Create empty file
		f = file(full_path, 'w')
		f.close()
		
		self.files.append(parent, (name, path, 'style'))
	
	def new_dir(self, name, selected):
		'''Create new directory'''
		parent, dir = self.find_parent_dir(selected)
		path = os.path.join(dir, name)
		full_path = os.path.join(self.dir, path)
		os.mkdir(full_path)
		
		self.files.append(parent, (name, path, 'dir'))
	
	def new_template(self, name):
		'''Create new template'''
		full_path = os.path.join(self.dir, '_oxalis', 'templates', name)
		# Create empty file
		f = file(full_path, 'w')
		f.close()
		
		self.templates.append((name, name, 'tpl'))
	
	def add_file(self, filename, selected):
		'''Add existing file to project'''
		parent, dir = self.find_parent_dir(selected)
		name = os.path.basename(filename)
		path = os.path.join(dir, name)
		full_path = os.path.join(self.dir, path)
		shutil.copyfile(filename, full_path)
		
		self.files.append(parent, (name, path, 'file'))
	
	def rename_file(self, selected, new_name):
		'''Rename selected file
		
		selected - tree iter of the selected file
		'''
		path, type = self.files.get(selected, 1, 2)
		full_path = os.path.join(self.dir, path)  # Make absolute path
		head, tail = os.path.split(path)
		if type == 'page':
			new_path = os.path.join(head, new_name[:-5]+'.text')
		else:
			new_path = os.path.join(head, new_name)
		new_full_path = os.path.join(self.dir, new_path)  # Make absolute path
		
		os.rename(full_path, new_full_path)
		
		# Rename also generated HTML
		if type == 'page':
			html_full_path = full_path[:-5]+'.html'
			if os.path.exists(html_full_path):
				html_new_full_path = new_full_path[:-5]+'.html'
				os.rename(html_full_path, html_new_full_path)
		
		self.files.set(selected, 0, new_name)
		self.files.set(selected, 1, new_path)
		return new_path
	
	def rename_template(self, selected, new_name):
		'''Rename selected template
		
		selected - tree iter of the selected template
		'''
		# TODO: Change name of template in all pages which use it
		name = self.templates.get_value(selected, 1)
		full_path = os.path.join(self.dir, '_oxalis', 'templates', name)
		new_full_path = os.path.join(self.dir, '_oxalis', 'templates', new_name)
		os.rename(full_path, new_full_path)
		
		self.templates.set(selected, 0, new_name)
		self.templates.set(selected, 1, new_name)
		return new_name
	
	def remove_file(self, selected):
		'''Remove selected file or directory
		
		selected - tree iter
		'''
		path, type = self.files.get(selected, 1, 2)
		path = os.path.join(self.dir, path)  # Make absolute path
		if type == 'dir':
			shutil.rmtree(path)
		else:
			os.remove(path)
		self.files.remove(selected)
	
	def remove_template(self, selected):
		'''Remove selected template
		
		selected - tree iter
		'''
		path = self.templates.get_value(selected, 1)
		# Make absolute path
		path = os.path.join(self.dir, '_oxalis', 'templates', path)
		os.remove(path)
		self.templates.remove(selected)
	
	def move_file(self, file_path, tree_path, position):
		'''Move file (used with drag&drop)
		
		file_path - relative path to the file
		tree_path - gtk.TreeStore path, where file was dropped
		position - position, where file was dropped
		Returns new file path if file was moved or None if not
		Caller should remove old item from tree store if move was successful
		'''
		iter = self.files.get_iter(tree_path)
		type = self.files.get_value(iter, 2)
		if (position == gtk.TREE_VIEW_DROP_BEFORE or
			position == gtk.TREE_VIEW_DROP_AFTER or
			type != 'dir'):
			iter = self.files.iter_parent(iter)
		if iter != None:
			dir_path = self.files.get_value(iter, 1)
		else:
			dir_path = ''
		file_dir, file_name = os.path.split(file_path)
		if file_dir == dir_path:
			return None  # File was dropped to the same directory
		else:
			src_path = os.path.join(self.dir, file_path)
			dest_path = os.path.join(self.dir, dir_path, file_name)
			shutil.move(src_path, dest_path)
			
			# Try to move also generated HTML file
			root, ext = os.path.splitext(file_name)
			if ext == '.text':
				html_src_path = os.path.join(self.dir, file_dir, root + '.html')
				if os.path.exists(html_src_path):
					html_dest_path = os.path.join(self.dir, dir_path,
						root + '.html')
					shutil.move(html_src_path, html_dest_path)
			
			# Add file to the tree store
			if os.path.isdir(dest_path):
				self.load_dir(os.path.join(dir_path, file_name), iter)
			else:
				self.load_file(file_name, os.path.join(dir_path, file_name), iter)
			return os.path.join(dir_path, file_name)
	
	def generate(self):
		'''Generate project output files'''
		self.files.foreach(self.generate_item)
	
	def generate_item(self, model, path, iter):
		type = model.get_value(iter, 2)
		if type == 'page':
			path = model.get_value(iter, 1)
			page = Page(path, self)
			page.generate()
	
	def upload(self):
		rcfile = os.path.join(self.dir, '_oxalis', 'sitecopyrc')
		storepath = os.path.join(self.dir, '_oxalis', 'sitecopy')
		
		# Update sitecopyrc file
		f = file(rcfile, 'w')
		tpl = string.Template(sitecopy_rc)
		f.write(tpl.substitute(dict(self.config.items('upload')),
			name='project', local=self.dir))
		f.close()
		
		if not os.path.exists(os.path.join(storepath, 'project')):
			sitecopy = subprocess.Popen(('sitecopy',
				'--rcfile='+rcfile, '--storepath='+storepath, '--init', 'project'))
			code = sitecopy.wait()
		self.sitecopy = subprocess.Popen(('sitecopy',
			'--rcfile='+rcfile, '--storepath='+storepath, '--update', 'project'))
	
	def check_upload(self):
		'''Checks if upload is completed
		
		Returns return code or None if upload is not completed.
		'''
		returncode = self.sitecopy.poll()
		return returncode
	
	def properties_dialog(self, parent_window):
		'''Display project properties dialog.'''
		settings = {}
		settings['upload'] = dict(self.config.items('upload'))
		settings['preview'] = dict(self.config.items('preview'))
		dialog = ProjectPropertiesDialog(parent_window, settings)
		response = dialog.run()
		settings = dialog.get_settings()
		dialog.destroy()
		
		if response == gtk.RESPONSE_OK:
			for section in settings:
				for key, value in settings[section].items():
					self.config.set(section, key, value)
			
			# Save properties
			f = file(os.path.join(self.dir, '_oxalis', 'config'), 'w')
			self.config.write(f)
			f.close


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
		print 'Hello', self.project.get_url_path()
	
	def get_url(self):
		print 'Hello', self.project.get_url_path()
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
		return 'http://127.0.0.1:8000/_oxalis?template=' + path
	
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

# vim:noet:nowrap
