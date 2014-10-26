# Oxalis Web Site Editor
#
# Copyright (C) 2005-2011 Sergej Chodarev
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

import mimetypes

from gi.repository import Gio, Gtk

from oxalis.site import SiteStore
from oxalis.util import open_editor


MENU = """
<interface>
  <menu id="menu">
    <section>
      <item>
        <attribute name="label" translatable="yes">Rename</attribute>
        <attribute name="action">win.rename-selected</attribute>
      </item>
      <item>
        <attribute name="label" translatable="yes">Delete</attribute>
        <attribute name="action">win.delete-selected</attribute>
      </item>
    </section>
  </menu>
</interface>
"""


class FilesBrowser:
    """Side panel with list of files and templates"""

    # Drag and Drop constants
    DND_FILE_PATH = 80
    DND_URI_LIST = 81

    def __init__(self, application, site):
        self.widget = Gtk.ScrolledWindow.new()
        self.widget.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.application = application
        self.site = site

        # Create tree views
        self.files_view = self._create_tree_view('files')
        self.widget.add(self.files_view)
        self.menu = self._setup_menu(self.files_view)

        # Fill views with data
        files_model = self.site.get_tree_model()
        self.files_view.set_model(files_model)
        self.files_view.set_reorderable(True)

    def get_selected(self):
        """Returns selected item in files_view

        Returns tuple: (model, iter)
        """
        selection = self.files_view.get_selection()
        selected = selection.get_selected()
        return selected

    def get_selected_document(self):
        """Return selected document in side pane.

        Returned object is subclass of site.File.
        """
        model, itr = self.get_selected()
        return model.get_value(itr, SiteStore.OBJECT_COL)

    def get_target_dir(self, position=Gtk.TreeViewDropPosition.INTO_OR_AFTER):
        """
        Find parent directory of selected file.

        If directory is selected, it will be returned.
        position is for usage with Drag and Drop.
        Returns directory object.
        """
        model, treeiter = self.get_selected()
        if treeiter is None:
            return self.site.store.get_by_path("")
        else:
            doc = model.get_value(treeiter, SiteStore.OBJECT_COL)
            if (position == Gtk.TreeViewDropPosition.BEFORE or
                    position == Gtk.TreeViewDropPosition.AFTER or
                    not doc.is_directory()):
                treeiter = model.iter_parent(treeiter)
            return model.get_value(treeiter, SiteStore.OBJECT_COL)

    ### Helpers ###

    def _create_tree_view(self, name):
        """Helper function for creating tree views for files and templates."""
        view = Gtk.TreeView()
        view.set_headers_visible(False)
        column = Gtk.TreeViewColumn()
        view.append_column(column)
        icon_cell = Gtk.CellRendererPixbuf()
        column.pack_start(icon_cell, False)
        column.set_cell_data_func(icon_cell, self._set_file_icon_cb)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'text', SiteStore.NAME_COL)
        view.set_search_column(SiteStore.NAME_COL)
        view.connect('row-activated', self._on_file_activated)
        selection = view.get_selection()
        selection.connect('changed', self._on_selection_changed, name)
        return view

    def _setup_menu(self, files_view):
        builder = Gtk.Builder.new_from_string(MENU, -1)
        menu_model = builder.get_object('menu')
        menu = Gtk.Menu.new_from_model(menu_model)
        # Connect to the files view
        menu.attach_to_widget(files_view)
        files_view.connect('button-press-event', self.on_button_press)
        files_view.connect('popup-menu', self.display_menu)
        return menu

    ### Callbacks ###

    def _set_file_icon_cb(self, column, cell, model, iter, __):
        doc = model.get_value(iter, SiteStore.OBJECT_COL)
        icon_theme = Gtk.IconTheme.get_default()
        if doc.is_directory():
            content_type = 'inode/directory'
        else:
            mime_type = mimetypes.guess_type(doc.name)[0]
            if mime_type is None:
                mime_type = 'text/plain'
            content_type = Gio.content_type_from_mime_type(mime_type)
        icon_names = Gio.content_type_get_icon(content_type)
        icon = icon_theme.choose_icon(icon_names.get_names(), 24, 0)
        if icon is not None:
            cell.set_property('pixbuf', icon.load_icon())
        else:
            cell.set_property('pixbuf', None)

    def _on_file_activated(self, tree_view, path, column):
        """Callback called when user doubleclicks on item in tree view"""
        store = tree_view.get_model()

        itr = store.get_iter(path)
        doc = store.get_value(itr, SiteStore.OBJECT_COL)

        open_editor(doc.full_path)

    def _on_selection_changed(self, selection, name):
        count = selection.count_selected_rows()
        if count == 0:
            self.application.enable_selection_actions(False)
        else:
            self.application.enable_selection_actions(True)

    def on_button_press(self, widget, event):
        if event.triggers_context_menu():
            self.display_menu(widget, event)

    def display_menu(self, widget, event=None):
        button = event.button if event else 0
        time = event.time if event else Gtk.get_current_event_time()
        self.menu.popup(None, None, None, None, button, time)
