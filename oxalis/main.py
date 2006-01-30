#! /usr/bin/env python

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

import pygtk
pygtk.require('2.0')
import gtk

import config
import project
import editor


name = 'Oxalis'
version = '0.1-alpha2'
comments = 'Web Site Editor'
copyright = 'Copyright \302\251 2005-2006 Sergej Chodarev'

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
      <menuitem action="DeleteSelected" />
      <separator />
      <menuitem action="Generate" />
      <menuitem action="Upload" />
      <separator />
      <menuitem action="Properties" />
      <separator />
      <menuitem action="Quit" />
    </menu>
    <menu action="EditMenu">
      <placeholder name="EditActions" />
      <separator />
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
		self.ui_manager = gtk.UIManager()
		accelgroup = self.ui_manager.get_accel_group()
		self.window.add_accel_group(accelgroup)
		self.ui_manager.add_ui_from_string(ui)
		
		app_actions = gtk.ActionGroup('app_actions')
		app_actions.add_actions((
			('ProjectMenu', None, 'Project'),
			('Quit', gtk.STOCK_QUIT, None, None, None, self.quit_cb),
			('EditMenu', None, 'Edit'),
			('Preferences', gtk.STOCK_PREFERENCES, None, None, None,
				self.preferences_cb),
			('HelpMenu', None, 'Help'),
			('About', gtk.STOCK_ABOUT, None, None, None, self.about_cb)
		))
		self.project_actions = gtk.ActionGroup('project_actions')
		self.project_actions.add_actions((
			('NewFile', gtk.STOCK_NEW, 'New File', ''),
			('NewPage', None, 'Page', None, None, self.new_page_cb),
			('NewStyle', None, 'Style (CSS)', None, None, self.new_style_cb),
			('NewDirectory', None, 'Directory', None, None, self.new_dir_cb),
			('NewTemplate', None, 'Template', None, None, self.new_template_cb),
			('AddFile', gtk.STOCK_ADD, 'Add File', None, None, self.add_file_cb),
			('DeleteSelected', gtk.STOCK_DELETE, 'Delete selected', None, None,
				self.delete_selected_cb),
			('Generate', None, 'Generate', None, None, self.generate_cb),
			('Upload', None, 'Upload', None, None, self.upload_cb),
			('Properties', gtk.STOCK_PROPERTIES, None, None, None,
				self.properties_cb)
		))
		self.project_actions.set_sensitive(False)
		
		self.ui_manager.insert_action_group(app_actions, 0)
		self.ui_manager.insert_action_group(self.project_actions, 0)
		menubar = self.ui_manager.get_widget('/MenuBar')
		
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
			if project.dir_is_project(dirname):
				self.load_project(dirname)
			else:
				# Display error message
				message = 'Selected directory is not valid Oxalis project'
				dlg = gtk.MessageDialog(parent=self.window,
					type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
					message_format=message)
				dlg.run()
				dlg.destroy()
	
	def create_paned(self):
		# Create tree view
		self.tree_view = gtk.TreeView()
		self.tree_view.set_headers_visible(False)
		column = gtk.TreeViewColumn()
		self.tree_view.append_column(column)
		icon_cell = gtk.CellRendererPixbuf()
		column.pack_start(icon_cell, False)
		column.set_cell_data_func(icon_cell, self.set_file_icon)
		cell = gtk.CellRendererText()
		column.pack_start(cell, True)
		column.add_attribute(cell, 'text', 0)
		self.tree_view.set_search_column(0)
		self.tree_view.connect('row-activated', self.file_activated)
		selection = self.tree_view.get_selection()
		selection.connect('changed', self.selection_changed_cb)
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
	
	def get_selected(self):
		'''Returns iter of selected item in tree_view'''
		selection = self.tree_view.get_selection()
		selected = selection.get_selected()
		return selected[1]  # selected is tuple (model, iter)

	def new_page_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Page')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				if not name.endswith('.html'):
					name += '.html'
				self.project.new_page(name, self.get_selected())
	
	def new_style_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Style')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				if not name.endswith('.css'):
					name += '.css'
				self.project.new_style(name, self.get_selected())
	
	def new_dir_cb(self, action):
		self.files_button.clicked()
		response, name = self.ask_name('Directory')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				self.project.new_dir(name, self.get_selected())
	
	def new_template_cb(self, action):
		self.templates_button.clicked()
		response, name = self.ask_name('Template')
		
		if response == gtk.RESPONSE_OK:
			if name != '':
				self.project.new_template(name)
	
	def add_file_cb(self, action):
		chooser = gtk.FileChooserDialog('Add File', parent=self.window,
			action=gtk.FILE_CHOOSER_ACTION_OPEN,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
				gtk.STOCK_OK, gtk.RESPONSE_OK))
		response = chooser.run()
		filename = chooser.get_filename()
		chooser.destroy()
		
		if response == gtk.RESPONSE_OK:
			self.project.add_file(filename, self.get_selected())
	
	def delete_selected_cb(self, action):
		'''Delete selected file, directory or template'''
		selected = self.get_selected()
		if self.active_component == 'files':
			name, type = self.project.files.get(selected, 0, 2)
		else:
			name, type = self.project.templates.get(selected, 0, 2)

		if type == 'dir':
			message = 'Delete directory "%(name)s" and its contents?' % {'name': name}
			message2 = 'If you delete the directory, all of its files and its subdirectories will be permanently lost.'
		else:
			message = 'Delete "%(name)s"?' % {'name': name}
			message2 = 'If you delete the item, it will be permanently lost.'
		
		# Create message dialog
		msg_dlg = gtk.MessageDialog(parent=self.window,
			type=gtk.MESSAGE_WARNING, message_format = message)
		msg_dlg.format_secondary_text(message2)
		msg_dlg.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			gtk.STOCK_DELETE, gtk.RESPONSE_OK)
		
		msg_dlg.show_all()
		response = msg_dlg.run()
		msg_dlg.destroy()

		if response == gtk.RESPONSE_OK:
			if self.active_component == 'files':
				self.project.remove_file(selected)
			else:
				self.project.remove_template(selected)
	
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
	
	def generate_cb(self, action):
		self.editor.save()
		self.project.generate()
	
	def upload_cb(self, action):
		self.project.upload()
	
	def properties_cb(self, action):
		self.project.properties_dialog(self.window)
	
	def selection_changed_cb(self, selection):
		count = selection.count_selected_rows()
		delete_action = self.project_actions.get_action('DeleteSelected')
		# If nothing is selected, DeleteSelected action should be insensitive
		if count == 0:
			delete_action.set_sensitive(False)
		else:
			delete_action.set_sensitive(True)
	
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
			self.tree_view.set_model(self.project.files)
		else:
			self.files_button.set_active(False)
			self.tree_view.set_model(self.project.templates)
		# Make DeleteSelected action insensitive while nothing is selected
		self.project_actions.get_action('DeleteSelected').set_sensitive(False)

	def file_activated(self, tree_view, path, column):
		store = tree_view.get_model()
		
		iter = store.get_iter(path)
		filename = store.get_value(iter, 1)
		type = store.get_value(iter, 2)
		
		if type != 'dir':
			# Unload old editor
			self.editor.save()
			self.paned.remove(self.editor)
			# Remove editor UI and actions
			self.ui_manager.remove_ui(self.editor_merge_id)
			self.ui_manager.remove_action_group(self.editor.edit_actions)
			# Load new editor
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
		self.project = project.Project(filename)
		
		self.create_paned()
		self.tree_view.set_model(self.project.files)
		
		self.vbox.remove(self.start_panel)
		self.vbox.pack_start(self.paned)
		self.paned.show_all()
		
		self.project_actions.set_sensitive(True)
		# Make DeleteSelected action insensitive while nothing is selected
		self.project_actions.get_action('DeleteSelected').set_sensitive(False)
		self.load_file(os.path.join(self.project.dir, 'index.text'), 'page')
		
	def load_file(self, filename, type):
		if type == 'page':
			page = project.Page(self.project, filename)
			self.editor = editor.PageEditor(page, self.project.templates)
		elif type == 'style':
			self.editor = editor.StyleEditor(filename)
		elif type == 'tpl':
			tpl = project.Template(self.project, filename)
			self.editor = editor.TemplateEditor(tpl)
		
		self.paned.add2(self.editor)
		self.editor.show_all()
		
		# Add editor UI and actions
		ui = self.editor.ui
		actions = self.editor.edit_actions
		self.editor_merge_id = self.ui_manager.add_ui_from_string(ui)
		self.ui_manager.insert_action_group(actions, 1)
		
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
