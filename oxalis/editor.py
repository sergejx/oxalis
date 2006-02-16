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

import os.path

import gtk
import pango
import gtksourceview
import gtkmozembed

import config


class Editor(gtk.VBox):
	ui = '''
<ui>
  <menubar name="MenuBar">
    <menu action="EditMenu">
      <placeholder name="EditActions">
        <menuitem action="Undo" />
        <menuitem action="Redo" />
        <separator />
        <menuitem action="Cut" />
        <menuitem action="Copy" />
        <menuitem action="Paste" />
      </placeholder>
    </menu>
  </menubar>
</ui>
'''
	
	def __init__(self, file, browser_has_toolbar=False):
		'''Constructor for Editor
		
		* file is object which represents file opened in editor, 
		these objects are defined in project.py
		* browser_has_toolbar - enables or disables toolbar
		with location entry in preview tab
		'''
		gtk.VBox.__init__(self)
		self.file = file
		self.browser = Browser(browser_has_toolbar)
		
		# Show file name above editor
		path = self.file.path
		if path.endswith('.text'):
			path = path[:-4] + 'html'
		editor_label = gtk.Label('<b>' + path + '</b>')
		editor_label.set_use_markup(True)
		editor_label.set_alignment(0, 0.5)
		editor_label.set_padding(4, 0)
		self.pack_start(editor_label, False, padding=4)
		
		notebook = gtk.Notebook()
		notebook.append_page(self.create_edit_page(), gtk.Label('Edit'))
		notebook.append_page(self.browser, gtk.Label('Preview'))
		notebook.connect('switch-page', self.switch_page)
		self.pack_start(notebook)
		
		self.set_text(file.text)
	
	def switch_page(self, notebook, page, page_num):
		if page_num == 1:  # Preview
			self.save()
			self.browser.load_url(self.file.url)


	def create_text_view(self, mime='text/html'):
		# Create text view
		self.buffer = gtksourceview.SourceBuffer()
		self.text_view = gtksourceview.SourceView(self.buffer)
		self.text_view.set_wrap_mode(gtk.WRAP_WORD)
		self.text_view.set_auto_indent(True)
		self.text_view.set_smart_home_end(True)
		self.set_font()
		lang_manager = gtksourceview.SourceLanguagesManager()
		lang = lang_manager.get_language_from_mime_type(mime)
		self.buffer.set_language(lang)
		self.buffer.set_highlight(True)
		
		# Create scrolled window
		text_scrolled = gtk.ScrolledWindow()
		text_scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		text_scrolled.add(self.text_view)
		
		self.create_actions()
		
		return text_scrolled
	
	create_edit_page = create_text_view
	
	def save(self):
		'''Save edited file'''
		text = self.buffer.get_text(
			self.buffer.get_start_iter(), self.buffer.get_end_iter())
		
		self.file.text = text
		self.file.write()
	
	def create_actions(self):
		'''Create editor ActionGroup and store it in self.edit_actions'''
		self.edit_actions = gtk.ActionGroup('edit_actions')
		self.edit_actions.add_actions((
			('Cut', gtk.STOCK_CUT, None, None, None, self.cut_cb),
			('Copy', gtk.STOCK_COPY, None, None, None, self.copy_cb),
			('Paste', gtk.STOCK_PASTE, None, None, None, self.paste_cb)
		))
		
		undo_action = gtk.Action('Undo', None, None, gtk.STOCK_UNDO)
		undo_action.connect('activate', self.undo_cb)
		undo_action.set_sensitive(False)
		self.edit_actions.add_action_with_accel(undo_action, '<Ctrl>Z')
		
		redo_action = gtk.Action('Redo', None, None, gtk.STOCK_REDO)
		redo_action.connect('activate', self.redo_cb)
		redo_action.set_sensitive(False)
		self.edit_actions.add_action_with_accel(redo_action, '<Ctrl><Shift>Z')
		
		self.buffer.connect('can-undo', self.change_undo_cb, undo_action)
		self.buffer.connect('can-redo', self.change_undo_cb, redo_action)
	
	def undo_cb(self, action):
		self.buffer.undo()
	def redo_cb(self, action):
		self.buffer.redo()
	def cut_cb(self, action):
		self.buffer.cut_clipboard(gtk.clipboard_get(), True)
	def copy_cb(self, action):
		self.buffer.copy_clipboard(gtk.clipboard_get())
	def paste_cb(self, action):
		self.buffer.paste_clipboard(gtk.clipboard_get(), None, True)
	def change_undo_cb(self, buffer, value, action):
		'''Change sensitivity of undo/redo action'''
		action.set_sensitive(value)
		
	def set_text(self, text):
		'''Set initial text of text buffer'''
		self.buffer.begin_not_undoable_action()
		self.buffer.set_text(text)
		self.buffer.end_not_undoable_action()
	
	def set_font(self):
		font = config.get('editor', 'font')
		self.text_view.modify_font(pango.FontDescription(font))


class PageEditor(Editor):
	def __init__(self, file):
		self.templates_store = file.project.templates
		Editor.__init__(self, file)

		if 'Title' in file.header:
			self.page_name_entry.set_text(file.header['Title'])
		if 'Template' in file.header:
			template = file.header['Template']
		else:
			template = 'default'
		
		self.templates_store.foreach(self.search_template, template)
	
	def search_template(self, model, path, iter, template):
		if model.get_value(iter, 0) == template:
			self.template_combo_box.set_active_iter(iter)
			return True
	
	def create_edit_page(self):
		self.page_name_entry = gtk.Entry()
		self.template_combo_box = gtk.ComboBox(self.templates_store)
		cell = gtk.CellRendererText()
		self.template_combo_box.pack_start(cell, True)
		self.template_combo_box.add_attribute(cell, 'text', 0)

		
		table = gtk.Table(3, 2)
		table.attach(gtk.Label('Title:'), 0, 1, 0, 1, 0, 0)
		table.attach(self.page_name_entry, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL, 0)
		table.attach(gtk.Label('Template:'), 0, 1, 1, 2, 0, 0)
		table.attach(self.template_combo_box, 1, 2, 1, 2, gtk.EXPAND|gtk.FILL, 0)
		table.attach(self.create_text_view(), 0, 2, 2, 3)
		
		return table
	
	def save(self):
		self.file.header['Title'] = self.page_name_entry.get_text()
		active = self.template_combo_box.get_active_iter()
		self.file.header['Template'] = self.templates_store.get_value(active, 0)
		
		Editor.save(self)


class TemplateEditor(Editor):
	def __init__(self, file):
		Editor.__init__(self, file)


class StyleEditor(Editor):
	def __init__(self, file):
		Editor.__init__(self, file, True)
		self.browser.load_url(self.file.url)
	
	def create_edit_page(self):
		return self.create_text_view('text/css')

	def switch_page(self, notebook, page, page_num):
		if page_num == 1:
			self.save()
			# For CSS we will not load default URL
			# but only reload page witch user has selected.
			self.browser.reload()


class Browser(gtk.VBox):
	'''Browser widget used for display preview'''
	def __init__(self, has_toolbar=True):
		'''Initialise Browser
		
		If has_toolbar is True, browser will have toolbar with address entry
		'''
		gtk.VBox.__init__(self)
		# Create GtkMozembed
		self.mozembed = gtkmozembed.MozEmbed()
		
		if has_toolbar:
			self.address_entry = gtk.Entry()
			self.address_entry.connect('activate', self.address_activate_cb)
			self.pack_start(self.address_entry, False)
			
			self.mozembed.connect('location', self.location_cb)
		
		self.pack_start(self.mozembed)
	
	def address_activate_cb(self, entry):
		address = entry.get_text()
		self.mozembed.load_url(address)
	
	def load_url(self, url):
		self.mozembed.load_url(url)
	
	def reload(self):
		self.mozembed.reload(gtkmozembed.FLAG_RELOADNORMAL)
	
	def location_cb(self, mozembed):
		'''Callback function called when browser location has changed'''
		address = mozembed.get_location()
		self.address_entry.set_text(address)
