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

import os.path

import gtk
import pango
import gtksourceview
import gtkmozembed

import config


class Editor(object):
	def create_text_view(self, mime='text/html'):
		# Create text view
		self.buffer = gtksourceview.SourceBuffer()
		self.text_view = gtksourceview.SourceView(self.buffer)
		self.text_view.set_wrap_mode(gtk.WRAP_WORD)
		self.set_font()
		lang_manager = gtksourceview.SourceLanguagesManager()
		lang = lang_manager.get_language_from_mime_type(mime)
		self.buffer.set_language(lang)
		self.buffer.set_highlight(True)
		
		# Create scrolled window
		text_scrolled = gtk.ScrolledWindow()
		text_scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		text_scrolled.add(self.text_view)
		
		return text_scrolled
	
	def set_font(self):
		font = config.get('editor', 'font')
		self.text_view.modify_font(pango.FontDescription(font))
	
class TabbedEditor(Editor, gtk.Notebook):
	def __init__(self):
		gtk.Notebook.__init__(self)
		
		# Create GtkMozembed
		self.mozembed = gtkmozembed.MozEmbed()

		self.append_page(self.create_text_view(), gtk.Label('Edit'))
		self.append_page(self.mozembed, gtk.Label('Preview'))
		self.connect('switch-page', self.switch_page)
	
	def show_all(self):
		gtk.Notebook.show_all(self)
		self.mozembed.realize()
	
	def switch_page(self, notebook, page, page_num):
		if page_num == 1:
			self.make_preview()


class PageEditor(TabbedEditor):
	def __init__(self, page, templates_store):
		self.templates_store = templates_store
		TabbedEditor.__init__(self)

		self.page = page
		if 'Title' in self.page.header:
			self.page_name_entry.set_text(self.page.header['Title'])
		if 'Template' in self.page.header:
			template = self.page.header['Template']
		else:
			template = 'default'
		
		self.templates_store.foreach(self.search_template, template)
		self.buffer.set_text(self.page.text)
	
	def search_template(self, model, path, iter, template):
		if model.get_value(iter, 0) == template:
			self.template_combo_box.set_active_iter(iter)
			return True
	
	def create_text_view(self):
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
		table.attach(Editor.create_text_view(self), 0, 2, 2, 3)
		
		return table
	
	def update_page(self):
		self.page.text = self.buffer.get_text(
			self.buffer.get_start_iter(), self.buffer.get_end_iter())
		self.page.header['Title'] = self.page_name_entry.get_text()
		active = self.template_combo_box.get_active_iter()
		self.page.header['Template'] = self.templates_store.get_value(active, 0)
		
	def make_preview(self):
		self.update_page()
		
		html = self.page.process_page()
		
		print html
		#print len(html)
		
		dir_uri = 'file://' + os.path.dirname(self.page.path) + '/'
		self.mozembed.open_stream(dir_uri, 'text/html')
		self.mozembed.append_data(html, long(len(html)))
		self.mozembed.close_stream()
	
	def save(self):
		self.update_page()
		self.page.write_page()


class TemplateEditor(TabbedEditor):
	def __init__(self, template):
		self.template = template
		TabbedEditor.__init__(self)
		self.buffer.set_text(self.template.text)
		
	def make_preview(self):
		text = self.buffer.get_text(
			self.buffer.get_start_iter(), self.buffer.get_end_iter())
		
		self.template.text = text
		
		html = text
		
		print html
		#print len(html)
		
		dir_uri = 'file://' + self.template.project.dir + '/'
		self.mozembed.open_stream(dir_uri, 'text/html')
		self.mozembed.append_data(html, long(len(html)))
		self.mozembed.close_stream()
		
	def save(self):
		text = self.buffer.get_text(
			self.buffer.get_start_iter(), self.buffer.get_end_iter())
		
		self.template.text = text
		self.template.write()

class StyleEditor(Editor, gtk.VBox):
	def __init__(self, filename):
		gtk.VBox.__init__(self)
		
		self.filename = filename
		
		self.pack_start(self.create_text_view('text/css'))
		
		f = file(filename)
		text = f.read()
		f.close()
		
		self.buffer.set_text(text)
	
	def save(self):
		text = self.buffer.get_text(
			self.buffer.get_start_iter(), self.buffer.get_end_iter())
		
		f = file(self.filename, 'w')
		f.write(text)
		f.close()
