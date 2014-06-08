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

from gi.repository import Gtk

import site

# Constants for column numbers
OBJECT_COL, NAME_COL, PATH_COL, TYPE_COL = range(4)

class SidePane(Gtk.VPaned):
    """Side panel with list of files and templates"""

    # Drag and Drop constants
    DND_FILE_PATH = 80
    DND_URI_LIST = 81

    # File type icons
    icons = {
        site.DIRECTORY: ['gnome-fs-directory', 'folder'],
        site.PAGE: ['gnome-mime-text-html', 'text-html'],
        site.STYLE: ['gnome-mime-text-css', 'text-x-css', 'text-x-generic'],
        site.FILE: ['gnome-mime-application', 'text-x-preview'],
        site.IMAGE: ['gnome-mime-image', 'image-x-generic'],
        site.TEMPLATE: ['text-x-generic-template'],
    }

    def __init__(self, application, site):
        Gtk.VPaned.__init__(self)
        self.application = application
        self.site = site

        # Create tree views
        self.files_view = self._create_tree_view('files')
        self.templates_view = self._create_tree_view('templates')

        # Create scrolled windows and labels
        files_box = self._create_scrolled_box('<b>Files</b>', self.files_view)
        templates_box = self._create_scrolled_box('<b>Templates</b>',
                                                 self.templates_view)

        # Pack everything
        self.pack1(files_box, resize=True)
        self.pack2(templates_box, resize=False)

        # Fill views with data
        files_model = self._fill_model(self.site.files)
        self.files_view.set_model(files_model)
        self.files_view.set_reorderable(True)

        templates_model = self._fill_model(self.site.templates)
        self.templates_view.set_model(templates_model)

    def get_selected(self):
        """Returns selected item in files_view

        Returns tuple: (model, iter)
        """
        selection = self.files_view.get_selection()
        if selection.count_selected_rows() == 0:
            selection = self.templates_view.get_selection()
        selected = selection.get_selected()
        return selected

    def get_selected_document(self):
        """Return selected document in side pane.

        Returned object is subclass of site.File.
        """
        model, itr = self.get_selected()
        return model.get_value(itr, OBJECT_COL)

    def get_target_dir(self, position=Gtk.TreeViewDropPosition.INTO_OR_AFTER):
        """
        Find parent directory of selected file.

        If directory is selected, it will be returned.
        position is for usage with Drag and Drop.
        Returns directory object.
        """
        model, treeiter = self.get_selected()
        if treeiter == None:
            return self.site.files[""]
        else:
            type = model.get_value(treeiter, TYPE_COL)
            if (position == Gtk.TREE_VIEW_DROP_BEFORE or
                position == Gtk.TREE_VIEW_DROP_AFTER or
                type != 'dir'):
                treeiter = model.iter_parent(treeiter)
            return model.get_value(treeiter, OBJECT_COL)

    ### Helpers ###
    
    def _fill_model(self, files):
        model = Gtk.TreeStore(object, str, str, int) # Document, path, name, type
        self._fill_directory(model, None, files[""])
        return model
        
    def _fill_directory(self, model, parent, directory):
        for child in directory.children:
            treeiter = model.append(parent,
                [child, child.path, child.name, self._document_type(child)])
            if isinstance(child, site.Directory):
                self._fill_directory(model, treeiter, child)
    
    def _document_type(self, document):
        if isinstance(document, site.Directory):
            return site.DIRECTORY
        elif isinstance(document, site.Template):
            return site.TEMPLATE
        else:
            return site.get_file_type(document.name)

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
        column.add_attribute(cell, 'text', NAME_COL)
        view.set_search_column(NAME_COL)
        view.connect('row-activated', self._on_file_activated)
        selection = view.get_selection()
        selection.connect('changed', self._on_selection_changed, name)
        return view

    def _create_scrolled_box(self, label_text, view):
        """Helper function for creating vbox with label and treeview in
           scrolled window.
        """
        box = Gtk.VBox()
        label = Gtk.Label()
        label.set_markup(label_text)
        label.set_alignment(0, 0.5)
        label.set_padding(6, 6)
        box.pack_start(label, False, False, 0)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(view)
        box.pack_start(scrolled, True, True, 0)
        return box

    ### Callbacks ###

    def _set_file_icon_cb(self, column, cell, model, iter, __):
        type = model.get_value(iter, TYPE_COL)
        icon_theme = Gtk.IconTheme.get_default()
        for icon_name in self.icons[type]:
            if icon_theme.has_icon(icon_name):
                icon = icon_theme.load_icon(icon_name, 24, 0)
                cell.set_property('pixbuf', icon)
                break
        else:
            cell.set_property('pixbuf', None)

    def _on_file_activated(self, tree_view, path, column):
        """Callback called when user doubleclicks on item in tree view"""
        store = tree_view.get_model()

        itr = store.get_iter(path)
        doc = store.get_value(itr, OBJECT_COL)

        self.application.load_file(doc)

    def _on_selection_changed(self, selection, name):
        count = selection.count_selected_rows()
        if count == 0:
            self.application.selection_actions.set_sensitive(False)
        else:
            # Remove selection from second list
            if name == 'files':
                self.templates_view.get_selection().unselect_all()
            if name == 'templates':
                self.files_view.get_selection().unselect_all()
            self.application.selection_actions.set_sensitive(True)

