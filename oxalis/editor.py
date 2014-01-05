# Oxalis Web Site Editor
#
# Copyright (C) 2005-2012 Sergej Chodarev
#
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

"""Editor component with preview."""

import gtk
import pango
import gtksourceview2
import webkit

import site
import config
import util

class NoEditorException(Exception):
    """Exception raised if no editor can be created for document."""
    pass


#   === Base Editor Class ===

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
        these objects are defined in site.py
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

        self.set_text(document.read())

    def set_editor_label(self):
        '''Display document path in editor label'''
        path = self.document.path
        self.editor_label.set_markup('<b>' + path + '</b>')


    def switch_page(self, notebook, page, page_num):
        if page_num == 1:  # Preview
            self.save()
            self.browser.load_url(self.document.url)


    def create_text_view(self, filename=None, mime=None):
        # Create text view
        self.buffer = gtksourceview2.Buffer()
        self.text_view = gtksourceview2.View(self.buffer)
        self.text_view.set_wrap_mode(gtk.WRAP_WORD)
        self.text_view.set_auto_indent(True)
        self.text_view.set_smart_home_end(True)
        self.set_font()
        lang_manager = gtksourceview2.LanguageManager()
        lang = lang_manager.guess_language(filename=filename, content_type=mime)
        self.buffer.set_language(lang)
        self.buffer.set_highlight_syntax(True)

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

    def create_edit_page(self):
        return self.create_text_view(filename=self.document.name)

    def drag_data_received_cb(self, widget, context, x, y, selection, info,
                              timestamp):
        if info == self.DND_FILE_PATH: # If file from side panel was dropped
            i = self.text_view.get_iter_at_location(x, y)
            # Construct absolute path to file
            path = '/' + self.document.site.get_url_path() + selection.data
            self.buffer.insert(i, path)
            context.finish(True, False, timestamp)

    def save(self):
        '''Save edited document'''
        if self.buffer.get_modified():
            text = self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter())
            self.document.write(text)
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

        self.buffer.connect('notify::can-undo', self.on_change_undo, undo_action)
        self.buffer.connect('notify::can-redo', self.on_change_undo, redo_action)

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
    def on_change_undo(self, buffer, prop, action):
        """Change sensitivity of undo/redo action"""
        action.set_sensitive(buffer.get_property(prop.name))

    def set_text(self, text):
        '''Set initial text of text buffer'''
        self.buffer.begin_not_undoable_action()
        self.buffer.set_text(text)
        self.buffer.end_not_undoable_action()
        self.buffer.set_modified(False)

    def set_font(self):
        font = config.settings.get('editor', 'font')
        self.text_view.modify_font(pango.FontDescription(font))


#   === Page Editor ===

class PageEditor(Editor):
    def __init__(self, document):
        Editor.__init__(self, document)
        if 'Title' in document.header:
            self.page_name_entry.set_text(document.header['Title'])

    def create_edit_page(self):
        self.page_name_entry = gtk.Entry()
        self.template_selector = TemplateSelector(self.document)

        table = util.make_table((
            ('Title:', self.page_name_entry),
            ('Template:', self.template_selector)
        ))
        table.set_col_spacings(6)
        table.set_border_width(2)

        vbox = gtk.VBox()
        vbox.pack_start(table, False)
        vbox.pack_start(self.create_text_view(self.document.name,
                                              mime="text/html"))
        return vbox

    def save(self):
        headers_modified = False

        title = self.page_name_entry.get_text()
        if ('Title' not in self.document.header or
           title != self.document.header['Title']):
            self.document.header['Title'] = title
            headers_modified = True

        template = self.template_selector.get_selected()
        if ('Template' not in self.document.header or
           template != self.document.header['Template']):
            self.document.header['Template'] = template
            headers_modified = True

        if self.buffer.get_modified() or headers_modified:
            text = self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter())
            self.document.write(text)
            self.buffer.set_modified(False)

class TemplateSelector(gtk.ComboBox):
    """Combo box for selecting page template."""
    # TODO: Move to ComboBoxText when porting to GTK 3

    def __init__(self, document):
        """
        Create template selector for a page and properly set selected template.
        """
        self.document = document
        templates_store = gtk.ListStore(str)
        super(TemplateSelector, self).__init__(templates_store)

        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)

        self.fill_store()

    def fill_store(self):
        # Site tempalates list also contains root item with empty name.
        # This item is used there as a marker for no template.
        for template in self.document.site.templates.documents():
            name = template.name
            i = self.get_model().append((name,))
            if name == self.document.header.get('Template', ''):
                self.set_active_iter(i)

    def get_selected(self):
        """Get the name of currently selected template."""
        active = self.get_active_iter()
        return self.get_model().get_value(active, 0)


#   === Other Editors ===

class TemplateEditor(Editor):
    def __init__(self, document):
        Editor.__init__(self, document)

    def create_edit_page(self):
        return self.create_text_view(mime="text/html")


class StyleEditor(Editor):
    def __init__(self, document):
        Editor.__init__(self, document, True)
        self.browser.load_url(self.document.url)

    def create_edit_page(self):
        return self.create_text_view(self.document.name)

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


#   === Browser ===

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

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled.add(self.webview)
        self.pack_start(scrolled)

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


def create_editor(doc):
    """Create appripriate editor for document."""
    if isinstance(doc, site.Page):
        return PageEditor(doc)
    elif isinstance(doc, site.Style):
        return StyleEditor(doc)
    elif isinstance(doc, site.Template):
        return TemplateEditor(doc)
    else:
        try: # if document can be readed as text
            doc.read()
            return Editor(doc)
        except ValueError:
            raise NoEditorException
