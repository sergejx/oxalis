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
import subprocess
import string
import re
from ConfigParser import RawConfigParser

import gtk

import markdown
import smartypants


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
	
	return path


class Project(object):
	def __init__(self, dir):
		self.dir = dir
		self.config = RawConfigParser()
		self.config.read(os.path.join(self.dir, '_oxalis', 'config'))
	
	def generate(self):
		for dirpath, dirnames, filenames in os.walk(self.dir):
			if dirpath == self.dir:
				dirnames.remove('_oxalis')
			for filename in filenames:
				name, ext = os.path.splitext(filename)
				path = os.path.join(dirpath, filename)
				if ext == '.text':
					page = Page(self, path)
					page.write_html()
	
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
		sitecopy = subprocess.Popen(('sitecopy',
			'--rcfile='+rcfile, '--storepath='+storepath, '--update', 'project'))
		
		code = sitecopy.wait()
		print '>', code
	
	def properties_dialog(self, parent_window):
		'''Display project properties dialog.'''
		settings = dict(self.config.items('upload'))
		dialog = ProjectPropertiesDialog(parent_window, settings)
		response = dialog.run()
		settings = dialog.get_settings()
		dialog.destroy()
		
		if response == gtk.RESPONSE_OK:
			for key, value in settings.items():
				self.config.set('upload', key, value)
			
			# Save properties
			f = file(os.path.join(self.dir, '_oxalis', 'config'), 'w')
			self.config.write(f)
			f.close


class Page(object):
	header_re = re.compile('(\w+): ?(.*)')
	
	def __init__(self, project, path):
		self.project = project
		self.path = path
		
		self.read_page()
	
	def read_page(self):
		page = file(self.path)
		self.header = {}
		self.text = ''
		in_body = False
		for line in page:
			if in_body:
				self.text += line
			elif line == '\n':
				in_body = True
			else:
				match = self.header_re.match(line)
				if match != None:
					self.header[match.group(1)] = match.group(2)
		page.close()
		#return (header, text)
	
	def write_page(self):
		f = file(self.path, 'w')
		for (key, value) in self.header.items():
			f.write(key + ': ' + value + '\n')
		f.write('\n')
		f.write(self.text)
		f.close()
	
	def process_page(self):
		html = markdown.markdown(self.text)
		html = smartypants.smartyPants(html)
		
		html = self.process_template(html)
		#print html
		#print len(html)
		
		return html
	
	def write_html(self):
		root, ext = os.path.splitext(self.path)
		f = file(root + '.html', 'w')
		f.write(self.process_page())
		f.close()
	
	def process_template(self, content):
		self.content = content
		if 'Template' in self.header:
			tpl_name = self.header['Template']
		else:
			tpl_name = 'default'

		f = file(os.path.join(self.project.dir, '_oxalis', 'templates', tpl_name), 'r')
		tpl = f.read()
		f.close()
		return re.sub('\{(\w+)\}', self.replace, tpl)
		
	def replace(self, match):
		tag = match.group(1)
		#print tag
		if tag == 'Content':
			return self.content
		elif tag in self.header:
			return self.header[tag]
		else:
			return ''

class Template(object):
	def __init__(self, project, path):
		self.project = project
		self.path = path
		
		f = file(path, 'r')
		self.text = f.read()
		f.close()
	
	def write(self):
		f = file(self.path, 'w')
		f.write(self.text)
		f.close()


class ProjectPropertiesDialog(gtk.Dialog):
	keys = ('host', 'user', 'passwd', 'remotedir')
	texts = {'host':'Host:',
		'user':'User:',
		'passwd':'Password:',
		'remotedir':'Remote Directory:'}
	
	def __init__(self, window = None, settings = {}):
		gtk.Dialog.__init__(self, 'Project Properties', window,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
				gtk.STOCK_OK, gtk.RESPONSE_OK))
		self.set_default_response(gtk.RESPONSE_OK)
		
		self.entries = {}
		for key in self.keys:
			self.entries[key] = gtk.Entry()
			if key in settings:
				self.entries[key].set_text(settings[key])
			label = gtk.Label(self.texts[key])
			hbox = gtk.HBox()
			hbox.pack_start(label)
			hbox.pack_start(self.entries[key])
			self.vbox.pack_start(hbox)
		self.entries['passwd'].set_visibility(False)
		
		self.vbox.show_all()
		
	def get_settings(self):
		settings = {}
		for key in self.keys:
			settings[key] = self.entries[key].get_text()
		return settings
