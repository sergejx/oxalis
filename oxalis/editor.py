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
import webkit

import config
import util


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

    # Drag and Drop constants
    DND_FILE_PATH = 80
    DND_TEXT = 81
    DND_TEXT_PLAIN = 82

    def __init__(self, document, browser_has_toolbar=False):
        '''Constructor for Editor

        * document is object which represents document opened in editor,
        these objects are defined in project.py
        * browser_has_toolbar - enables or disables toolbar
        with location entry in preview tab
        '''
        gtk.VBox.__init__(self)
        self.document = document
        self.browser = Browser(browser_has_toolbar)

        # Create label above editor for displaying document path
        self.editor_label = gtk.Label()
        self.set_editor_label()
        self.editor_label.set_alignment(0, 0.5)
        self.editor_label.set_padding(4, 0)
        self.pack_start(self.editor_label, False, padding=4)

        notebook = gtk.Notebook()
        notebook.append_page(self.create_edit_page(), gtk.Label('Edit'))
        notebook.append_page(self.browser, gtk.Label('Preview'))
        notebook.connect('switch-page', self.switch_page)
        self.pack_start(notebook)

        self.set_text(document.text)

    def set_editor_label(self):
        '''Display document path in editor label'''
        path = self.document.path
        self.editor_label.set_markup('<b>' + path + '</b>')


    def switch_page(self, notebook, page, page_num):
        if page_num == 1:  # Preview
            self.save()
            self.browser.load_url(self.document.url)


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

        self.text_view.drag_dest_set(0,
            [('TEXT', 0, self.DND_TEXT),
            ('text/plain', 0, self.DND_TEXT_PLAIN),
            ('file-path', gtk.TARGET_SAME_APP, self.DND_FILE_PATH)],
            gtk.gdk.ACTION_COPY)
        self.text_view.connect('drag-data-received',
                               self.drag_data_received_cb)

        # Create scrolled window
        text_scrolled = gtk.ScrolledWindow()
        text_scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        text_scrolled.add(self.text_view)

        self.create_actions()

        return text_scrolled

    create_edit_page = create_text_view

    def drag_data_received_cb(self, widget, context, x, y, selection, info,
                              timestamp):
        if info == self.DND_FILE_PATH: # If file from side panel was dropped
            i = self.text_view.get_iter_at_location(x, y)
            # Construct absolute path to file
            path = '/' + self.document.project.get_url_path() + selection.data
            self.buffer.insert(i, path)
            context.finish(True, False, timestamp)

    def save(self):
        '''Save edited document'''
        if self.buffer.get_modified():
            text = self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter())
            self.document.text = text
            self.document.write()
            self.buffer.set_modified(False)

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
        self.buffer.set_modified(False)

    def set_font(self):
        font = config.get('editor', 'font')
        self.text_view.modify_font(pango.FontDescription(font))


class PageEditor(Editor):
    def __init__(self, document):
        self.templates_store = document.project.templates
        Editor.__init__(self, document)

        if 'Title' in document.header:
            self.page_name_entry.set_text(document.header['Title'])
        if 'Template' in document.header:
            template = document.header['Template']
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

        table = util.make_table((
            ('Title:', self.page_name_entry),
            ('Template:', self.template_combo_box)
        ))
        table.set_col_spacings(6)
        table.set_border_width(2)

        vbox = gtk.VBox()
        vbox.pack_start(table, False)
        vbox.pack_start(self.create_text_view())

        return vbox

    def save(self):
        modified = False

        title = self.page_name_entry.get_text()
        if ('Title' not in self.document.header or
           title != self.document.header['Title']):
            self.document.header['Title'] = title
            modified = True

        active = self.template_combo_box.get_active_iter()
        template = self.templates_store.get_value(active, 0)
        if ('Template' not in self.document.header or
           template != self.document.header['Template']):
            self.document.header['Template'] = template
            modified = True

        if self.buffer.get_modified():
            text = self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter())
            self.document.text = text
            modified = True

        if modified:
            self.document.write()
            self.buffer.set_modified(False)


class TemplateEditor(Editor):
    def __init__(self, document):
        Editor.__init__(self, document)


class StyleEditor(Editor):
    def __init__(self, document):
        Editor.__init__(self, document, True)
        self.browser.load_url(self.document.url)

    def create_edit_page(self):
        return self.create_text_view('text/css')

    def switch_page(self, notebook, page, page_num):
        if page_num == 1:
            self.save()
            # For CSS we will not load default URL
            # but only reload page witch user has selected.
            self.browser.reload()


class DummyEditor(gtk.Label):
    '''Dummy editor, used when no document is opened.'''
    class DummyDocument:
        pass
    def __init__(self):
        gtk.Label.__init__(self)
        self.ui = ''
        self.edit_actions = gtk.ActionGroup('edit_actions')
        self.document = self.DummyDocument()
        self.document.path = None
    def save(self): pass
    def set_font(self): pass


class Browser(gtk.VBox):
    """
    Browser widget for displaying preview.

    WebKit is used as rendering engine.

    Public methods:

    * load_url(url)
    * reload()
    """

    def __init__(self, has_toolbar=True):
        """Create new browser widget.

        If `has_toolbar` is True, browser will have toolbar with address entry.
        """
        gtk.VBox.__init__(self)
        self.webview = webkit.WebView()

        if has_toolbar:
            self.address_entry = gtk.Entry()
            self.address_entry.connect('activate',
                                       self.on_address_entry_activated)
            self.pack_start(self.address_entry, False)

            self.webview.connect('navigation-requested',
                                 self.on_navigation_requested)

        self.pack_start(self.webview)

    def load_url(self, url):
        self.webview.open(url)

    def reload(self):
        self.webview.reload()

    def on_address_entry_activated(self, entry):
        address = entry.get_text()
        self.load_url(address)

    def on_navigation_requested(self, page, frame, request):
        """Callback function called when browser is going to load new URL."""
        uri = request.get_uri()
        self.address_entry.set_text(uri)
        return False # Continue loading page

# vim:tabstop=4:expandtab
