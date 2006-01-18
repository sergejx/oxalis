# Oxalis Web Editor
#
# Copyright (C) 2005 Sergej Chodarev

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

def create_project(path, upload_settings):
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
	for key, value in upload_settings.items():
		config.set('upload', key, value)
	f = file(config_file, 'w')
	config.write(f)
	f.close()
	
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
	
	# Sitecopy configuration
	f = file(os.path.join(oxalis_dir, 'sitecopyrc'), 'w')
	tpl = string.Template(sitecopy_rc)
	f.write(tpl.substitute(upload_settings, name='project', local=path))
	f.close()
	os.chmod(os.path.join(oxalis_dir, 'sitecopyrc'), 0600)
		
	# Sitecopy storepath
	os.mkdir(os.path.join(oxalis_dir, 'sitecopy'))
	os.chmod(os.path.join(oxalis_dir, 'sitecopy'), 0700)
	
	return path


class Project(object):
	def __init__(self, dir):
		self.dir = dir
	
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
		if not os.path.exists(os.path.join(storepath, 'project')):
			sitecopy = subprocess.Popen(('sitecopy',
				'--rcfile='+rcfile, '--storepath='+storepath, '--init', 'project'))
			code = sitecopy.wait()
		sitecopy = subprocess.Popen(('sitecopy',
			'--rcfile='+rcfile, '--storepath='+storepath, '--update', 'project'))
		
		code = sitecopy.wait()
		print '>', code


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
