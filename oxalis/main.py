#! /usr/bin/env python

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
import shutil

import pygtk
pygtk.require('2.0')
import gtk

import config
import project
import editor


name = 'Oxalis'
version = '0.0.0'
comments = 'Web Editor'
copyright = 'Copyright \302\251 2005 Sergej Chodarev'

ui = '''
<ui>
  <menubar name="MenuBar">
    <menu action="ProjectMenu">
      <menu action="NewFile">
        <menuitem action="NewPage" />
        <menuitem action="NewStyle" />
        <menuitem action="NewDirectory" />
        <menuitem action="NewTemplate" />
      </menu>
      <menuitem action="AddFile" />
      <separator />
      <menuitem action="Generate" />
      <menuitem action="Upload" />
      <separator />
      <menuitem action="Properties" />
      <separator />
      <menuitem action="Quit" />
    </menu>
    <menu action="EditMenu">
      <menuitem action="Preferences" />
    </menu>
    <menu action="HelpMenu">
      <menuitem action="About" />
    </menu>
  </menubar>
</ui>
'''

class Oxalis(object):
	icons = {
		'dir': 'gnome-fs-directory',
		'page': 'gnome-mime-text-html',
		'style': 'gnome-mime-text-css',
		'file': 'gnome-mime-application'}

	def make_window(self):
		self.window = gtk.Window()
		self.window.set_title('Oxalis')
		self.window.connect_after('delete-event', self.quit_cb)
		
		# Create menu bar
		ui_manager = gtk.UIManager()
		accelgroup = ui_manager.get_accel_group()
		self.window.add_accel_group(accelgroup)
		ui_manager.add_ui_from_string(ui)
		
		actions = gtk.ActionGroup('actions')
		actions.add_actions((
			('ProjectMenu', None, 'Project'),
			('NewFile', gtk.STOCK_NEW, 'New File', ''),
			('NewPage', None, 'Page', None, None, self.new_page_cb),
			('NewStyle', None, 'Style (CSS)', None, None, self.new_style_cb),
			('NewDirectory', None, 'Directory', None, None, self.new_dir_cb),
			('NewTemplate', None, 'Template', None, None, self.new_template_cb),
			('AddFile', gtk.STOCK_ADD, 'Add File', None, None, self.add_file_cb),
			('Generate', None, 'Generate', None, None, self.generate_cb),
			('Upload', None, 'Upload', None, None, self.upload_cb),
			('Properties', gtk.STOCK_PROPERTIES, None, None, None, self.properties_cb),
			('Quit', gtk.STOCK_QUIT, None, None, None, self.quit_cb),
			('EditMenu', None, 'Edit'),
			('Preferences', gtk.STOCK_PREFERENCES, None, None, None, self.preferences_cb),
			('HelpMenu', None, 'Help'),
			('About', gtk.STOCK_ABOUT, None, None, None, self.about_cb)
		))
		
		ui_manager.insert_action_group(actions, 0)
		menubar = ui_manager.get_widget('/MenuBar')
		
		self.vbox = gtk.VBox()
		self.vbox.pack_start(menubar, False)
		
		self.create_start_panel()
		
		self.window.add(self.vbox)
		
		width = config.getint('window', 'width')
		height = config.getint('window', 'height')
		self.window.resize(width, height)
		

		config.add_notify('editor', 'font', self.font_changed)
		
	def create_start_panel(self):
		new = gtk.Button('New project')
		icon = gtk.image_new_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_BUTTON)
		new.set_image(icon)
		new.connect('clicked', self.new_project_cb)
		
		open = gtk.Button('Open project')
		icon = gtk.image_new_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
		open.set_image(icon)
		open.connect('clicked', self.open_project_cb)
		
		box = gtk.VBox()
		box.pack_start(new)
		box.pack_start(open)
		self.start_panel = gtk.Alignment(0.5, 0.5, 0.2, 0.0)
		self.start_panel.add(box)
		self.vbox.pack_start(self.start_panel)
	
	def new_project_cb(self, *args):
		chooser = gtk.FileChooserDialog(
			'New Project', action=gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER,
			buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			'Create', gtk.RESPONSE_OK))
		response = chooser.run()
		dirname = chooser.get_filename()
		chooser.destroy()
		
		if response == gtk.RESPONSE_OK:
			project.create_project(dirname)
			self.load_project(dirname)
	
	def open_project_cb(self, *args):
		chooser = gtk.FileChooserDialog(
			'Open Project', action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
			buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		response = chooser.run()
		dirname = chooser.get_filename()
		chooser.destroy()
		
		if response == gtk.RESPONSE_OK:
			self.load_project(dirname)
	
	def create_paned(self):
		# Create tree view
		self.tree_view = gtk.TreeView()
		self.tree_view.set_headers_visible(False)
		self.column = gtk.TreeViewColumn()
		self.tree_view.append_column(self.column)
		icon_cell = gtk.CellRendererPixbuf()
		self.column.pack_start(icon_cell, False)
		self.column.set_cell_data_func(icon_cell, self.set_file_icon)
		self.cell = gtk.CellRendererText()
		self.column.pack_start(self.cell, True)
		self.column.add_attribute(self.cell, 'text', 0)
		self.tree_view.set_search_column(0)
		self.tree_view.connect('row-activated', self.file_activated)
		# Create scrolled window
		tree_scrolled = gtk.ScrolledWindow()
		tree_scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		tree_scrolled.add(self.tree_view)
		
		# Create navigation buttons
		self.files_button = gtk.ToggleButton('Files')
		self.files_button.connect('clicked', self.nav_button_clicked, 'files')
		self.templates_button = gtk.ToggleButton('Templates')
		self.templates_button.connect('clicked', self.nav_button_clicked, 'templates')
		self.active_component = 'files'
		self.files_button.set_active(True)
		
		# Create navigation panel
		nav_panel = gtk.VBox()
		nav_panel.pack_start(tree_scrolled)
		nav_panel.pack_start(self.files_button, False)
		nav_panel.pack_start(self.templates_button, False)
		
		self.paned = gtk.HPaned()
		self.paned.add1(nav_panel)
		
		self.paned.set_position(config.getint('window', 'sidepanel-width'))
	
	def font_changed(self):
		self.editor.set_font()

	def new_page_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Page')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				if name.endswith('.html'):
					basename = name[0:-5]
				else:
					basename = name
					name += '.html'
					
				parent, dir = self.get_selected_dir()
				path = os.path.join(dir, basename+'.text')
				
				# Create page
				f = file(path, 'w')
				f.write('\n')
				f.close()
				
				iter = self.files_store.append(parent, (name, path, 'page'))
	
	def new_style_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Style')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				if not name.endswith('.css'):
					name += '.css'
					
				parent, dir = self.get_selected_dir()
				path = os.path.join(dir, name)
				
				# Create page
				f = file(path, 'w')
				f.close()
				
				iter = self.files_store.append(parent, (name, path, 'style'))
	
	def new_dir_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Directory')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				parent, dir = self.get_selected_dir()
				path = os.path.join(dir, name)
				
				# Create directory
				os.mkdir(path)
				
				iter = self.files_store.append(parent, (name, path, 'dir'))
	
	def new_template_cb(self, action):
		self.templates_button.clicked()
		response, name = self.ask_name('Template')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				path = os.path.join(self.project.dir, '_oxalis', 'templates', name)
				
				# Create template
				f = file(path, 'w')
				f.close()
				
				iter = self.templates_store.append((name, path, 'tpl'))
	
	def add_file_cb(self, action):
		chooser = gtk.FileChooserDialog('Add File', parent=self.window,
			action=gtk.FILE_CHOOSER_ACTION_OPEN,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
				gtk.STOCK_OK, gtk.RESPONSE_OK))
		response = chooser.run()
		filename = chooser.get_filename()
		chooser.destroy()
		
		if response == gtk.RESPONSE_OK:
			parent, dir = self.get_selected_dir()
			name = os.path.basename(filename)
			path = os.path.join(dir, name)
			
			shutil.copyfile(filename, path)
			
			iter = self.files_store.append(parent, (name, path, 'file'))
	
	def ask_name(self, title):
		dialog = gtk.Dialog('New '+title, self.window, 
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
				gtk.STOCK_OK, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		
		label = gtk.Label('Name:')
		entry = gtk.Entry()
		hbox = gtk.HBox()
		hbox.pack_start(label)
		hbox.pack_start(entry)
		dialog.vbox.pack_start(hbox)
		hbox.show_all()
		
		response = dialog.run()
		name = entry.get_text()
		dialog.destroy()
		return response, name
	
	def get_selected_dir(self):
		'''Find selectected directory or parent directory of selected file
		If nothing is selected, returns None and base dir of project
		Returns tuple (iter, dir)'''
		model, selected = self.tree_view.get_selection().get_selected()
		if selected == None:
			parent = None
			dir = self.project.dir
		elif model.get_value(selected, 2) == 'dir':
			parent = selected
			dir = model.get_value(selected, 1)
		else:
			parent = model.iter_parent(selected)
			if parent != None:
				dir = model.get_value(parent, 1)
			else:
				dir = self.project.dir
		return parent, dir
	
	def generate_cb(self, action):
		self.editor.save()
		self.project.generate()
	
	def upload_cb(self, action):
		self.project.upload()
	
	def properties_cb(self, action):
		self.project.properties_dialog(self.window)
	
	def nav_button_clicked(self, button, param):
		if self.active_component == param:
			button.set_active(True)
		else:
			if button.get_active() == True:
				self.active_component = param
				self.switch_component(param)
	
	def switch_component(self, component):
		self.active_component = component
		if component == 'files':
			self.templates_button.set_active(False)
			self.tree_view.set_model(self.files_store)
		else:
			self.files_button.set_active(False)
			self.tree_view.set_model(self.templates_store)

	def file_activated(self, tree_view, path, column):
		store = tree_view.get_model()
		
		i = store.get_iter(path)
		filename = store.get_value(i, 1)
		type = store.get_value(i, 2)
		
		self.editor.save()
		self.load_file(filename, type)
	
	def set_file_icon(self, column, cell, model, iter):
		type = model.get_value(iter, 2)
		if type != 'tpl':
			icon_theme = gtk.icon_theme_get_default()
			icon = icon_theme.load_icon(self.icons[type], 24, 0)
			cell.set_property('pixbuf', icon)
		else:
			cell.set_property('pixbuf', None)
		
	def load_project(self, filename):
		self.create_paned()
		
		self.project = project.Project(filename)

		# Create files tree store
		# diaplay_name, path, type
		# type can be: dir, page, style, file, tpl
		self.files_store = gtk.TreeStore(str, str, str)
		self.files_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
		
		parent = None
		for dirpath, dirnames, filenames in os.walk(self.project.dir):
			if dirpath == self.project.dir:
				dirnames.remove('_oxalis')
			else:
				name = os.path.basename(dirpath)
				parent = self.files_store.append(parent, (name, dirpath, 'dir'))
			for filename in filenames:
				name, ext = os.path.splitext(filename)
				path = os.path.join(dirpath, filename)
				if ext == '.text':
					name += '.html'
					self.files_store.append(parent, (name, path, 'page'))
				elif ext == '.css':
					name = filename
					self.files_store.append(parent, (name, path, 'style'))
				elif ext not in ('.web','.html') and filename[0] not in ('.','_'):
					name = filename
					self.files_store.append(parent, (name, path, 'file'))
		
		self.tree_view.set_model(self.files_store)
		
		# Create templates tree store
		self.templates_store = gtk.ListStore(str, str, str)
		
		for filename in os.listdir(os.path.join(self.project.dir, '_oxalis', 'templates')):
			name = os.path.basename(filename)
			path = os.path.join(self.project.dir, '_oxalis', 'templates', filename)
			self.templates_store.append((name, path, 'tpl'))
		
		
		self.vbox.remove(self.start_panel)
		self.vbox.pack_start(self.paned)
		self.paned.show_all()
		self.load_file(os.path.join(self.project.dir, 'index.text'), 'page')
		
	def load_file(self, filename, type):
		if type != 'dir':
			if 'editor' in self.__dict__: # this should be done more elegantly
				self.paned.remove(self.editor)
		
		if type == 'page':
			page = project.Page(self.project, filename)
			self.editor = editor.PageEditor(page, self.templates_store)
		elif type == 'style':
			self.editor = editor.StyleEditor(filename)
		elif type == 'tpl':
			tpl = project.Template(self.project, filename)
			self.editor = editor.TemplateEditor(tpl)
		
		self.paned.add2(self.editor)
		self.editor.show_all()
		print filename
		
	def run(self):
		self.make_window()
		self.window.show_all()
		gtk.main()
	
	def preferences_cb(self, action):
		pref = PreferencesDialog(self.window)
		pref.run()
		pref.destroy()
	
	def about_cb(self, action):
		about = gtk.AboutDialog()
		about.set_name(name)
		about.set_version(version)
		about.set_comments(comments)
		about.set_copyright(copyright)
		about.run()
		about.destroy()
			
	def quit_cb(self, *args):
		if 'editor' in self.__dict__:
			self.editor.save()

		width, height = self.window.get_size()
		config.set('window', 'width', width)
		config.set('window', 'height', height)
		if 'paned' in self.__dict__:
			config.set('window', 'sidepanel-width', self.paned.get_position())
		gtk.main_quit()


class PreferencesDialog(gtk.Dialog):
	def __init__(self, parent):
		buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
		gtk.Dialog.__init__(self, 'Oxalis Preferences', parent, buttons=buttons)
		label = gtk.Label('Editor font:')
		font_button = gtk.FontButton(config.get('editor', 'font'))
		font_button.connect('font-set', self.font_set)
		box = gtk.HBox()
		box.pack_start(label)
		box.pack_start(font_button)
		self.vbox.pack_start(box)
		self.show_all()
	
	def font_set(self, font_button):
		print font_button.get_font_name()
		config.set('editor', 'font', font_button.get_font_name())


def run():
	config.init()
	Oxalis().run()
	config.write()
