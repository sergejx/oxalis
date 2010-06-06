# Oxalis Web Editor
#
# Copyright (C) 2005-2010 Sergej Chodarev

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

import gtk

import document

# Constants for column numbers
OBJECT_COL, NAME_COL, PATH_COL, TYPE_COL = range(4)

class FilesTreeModel(gtk.GenericTreeModel):
    """Tree Model for project files and templates."""
    columns = [object, str, str, str] # Document, path, name, type

    def __init__(self, files):
        """Create new model with specified files dictionary."""
        gtk.GenericTreeModel.__init__(self)
        self.files = files

    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(self.columns)

    def on_get_column_type(self, index):
        return self.columns[index]

    def on_get_iter(self, tree_path):
        # File objects are used to create tree iters
        def find_tree_path(parent, tree_path):
            if tree_path:
                i = tree_path[0]
                return find_tree_path(parent.children[i], tree_path[1:])
            else:
                return parent
        return find_tree_path(self.files[""], tree_path)

    def on_get_path(self, rowref):
        path = []
        item = rowref
        while item.path != "":
            siblings = item.parent.children
            i = siblings.index(item)
            path.insert(0, i)
            item = item.parent
        return tuple(path)

    def on_get_value(self, rowref, column):
        if column == OBJECT_COL:
            return rowref
        elif column == NAME_COL:
            return rowref.name
        elif column == PATH_COL:
            return rowref.path
        elif column == TYPE_COL: # TODO return icons itself
            if isinstance(rowref, document.Directory):
                return 'dir'
            elif isinstance(rowref, document.Template):
                return 'tpl'
            else:
                return document.get_file_type(rowref.name)

    def on_iter_next(self, rowref):
        siblings = rowref.parent.children
        i = siblings.index(rowref)
        try:
            return siblings[i+1]
        except IndexError:
            return None

    def on_iter_children(self, parent):
        if parent is None:
            parent = self.files[""]
        return parent.children[0]

    def on_iter_has_child(self, rowref):
        if rowref.children:
            return True
        else:
            return False

    def on_iter_n_children(self, rowref):
        if rowref is None:
            rowref = self.files[""]
        return len(rowref.children)

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            parent = self.files[""]
        return parent.children[n]

    def on_iter_parent(self, child):
        return child.parent

    # Events from files list #
    def on_add(self, path):
        f = self.files[path]
        self.row_inserted(self.on_get_path(f), self.create_tree_iter(f))

    def on_remove(self, path):
        obj = self.files[path]
        tree_path = self.on_get_path(obj)
        del self.files[path]
        self.row_deleted(tree_path)

class SidePane(gtk.VPaned):
    """Side panel with list of files and templates"""

    # Drag and Drop constants
    DND_FILE_PATH = 80
    DND_URI_LIST = 81

    # File type icons
    icons = {
        'dir': ['gnome-fs-directory', 'folder'],
        'page': ['gnome-mime-text-html', 'text-html'],
        'style': ['gnome-mime-text-css', 'text-x-css', 'text-x-generic'],
        'file': ['gnome-mime-application', 'text-x-preview'],
        'image': ['gnome-mime-image', 'image-x-generic'],
        'tpl': ['text-x-generic-template']
    }

    def __init__(self, application, project):
        gtk.VPaned.__init__(self)
        self.application = application
        self.project = project

        # Create tree views
        self.files_view = self._create_tree_view('files')
        self.templates_view = self._create_tree_view('templates')

#        # Set up Drag and Drop
#        self.files_view.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
#            [('file-path', gtk.TARGET_SAME_APP, self.DND_FILE_PATH)],
#            gtk.gdk.ACTION_MOVE | gtk.gdk.ACTION_COPY)
#        self.files_view.enable_model_drag_dest(
#            [('file-path', gtk.TARGET_SAME_APP | gtk.TARGET_SAME_WIDGET,
#              self.DND_FILE_PATH),
#            ('text/uri-list', 0, self.DND_URI_LIST)],
#            gtk.gdk.ACTION_MOVE)
#        self.files_view.connect("drag-data-get",
#            self._tree_drag_data_get_cb)
#        self.files_view.connect("drag-data-received",
#            self._tree_drag_data_received_cb)

        # Create scrolled windows and labels
        files_box = self._create_scrolled_box('<b>Files</b>', self.files_view)
        templates_box = self._create_scrolled_box('<b>Templates</b>',
                                                 self.templates_view)

        # Pack everything
        self.pack1(files_box, resize=True)
        self.pack2(templates_box, resize=False)

        # Fill views with data
        self.files_view.set_model(FilesTreeModel(self.project.files))
        self.project.files_observer = self.files_view.get_model()
        self.templates_view.set_model(FilesTreeModel(self.project.templates))
        self.project.templates_observer = self.templates_view.get_model()

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

        Returned object is subclass of document.Document.
        """
        model, itr = self.get_selected()
        return model.get_value(itr, OBJECT_COL)

    def get_target_dir(self, position=gtk.TREE_VIEW_DROP_INTO_OR_AFTER):
        """
        Find parent directory of selected file.

        If directory is selected, it will be returned.
        position is for usage with Drag and Drop.
        Returns directory object.
        """
        model, treeiter = self.get_selected()
        if treeiter == None:
            return self.project.files[""]
        else:
            type = model.get_value(treeiter, TYPE_COL)
            if (position == gtk.TREE_VIEW_DROP_BEFORE or
                position == gtk.TREE_VIEW_DROP_AFTER or
                type != 'dir'):
                treeiter = model.iter_parent(treeiter)
            return model.get_value(treeiter, OBJECT_COL)

    ### Helpers ###

    def _create_tree_view(self, name):
        """Helper function for creating tree views for files and templates."""
        view = gtk.TreeView()
        view.set_headers_visible(False)
        column = gtk.TreeViewColumn()
        view.append_column(column)
        icon_cell = gtk.CellRendererPixbuf()
        column.pack_start(icon_cell, False)
        column.set_cell_data_func(icon_cell, self._set_file_icon_cb)
        cell = gtk.CellRendererText()
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
        box = gtk.VBox()
        label = gtk.Label()
        label.set_markup(label_text)
        label.set_alignment(0, 0.5)
        label.set_padding(6, 6)
        box.pack_start(label, False)
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled.add(view)
        box.pack_start(scrolled)
        return box

    ### Callbacks ###

    def _set_file_icon_cb(self, column, cell, model, iter):
        type = model.get_value(iter, TYPE_COL)
        icon_theme = gtk.icon_theme_get_default()
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

#    def _tree_drag_data_get_cb(self,
#            treeview, context, selection, info, timestamp):
#        tree_selection = treeview.get_selection()
#        model, iter = tree_selection.get_selected()
#        file_path = model.get_value(iter, PATH_COL)
#        selection.set('file-path', 8, file_path)

#    def _tree_drag_data_received_cb(self,
#            treeview, context, x, y, selection, info, timestamp):
#        drop_info = treeview.get_dest_row_at_pos(x, y)
#        if drop_info == None:  # if item was dropped after last tree item
#            drop_info = (len(treeview.get_model())-1,), gtk.TREE_VIEW_DROP_AFTER
#        tree_path, position = drop_info

#        if info == self.DND_FILE_PATH: # From Oxalis itself
#            file_path = selection.data
#            new_path = self.project.move_file(file_path, tree_path, position)
#            if new_path != None:
#                context.finish(True, True, timestamp)
#                # If moved file is opened in editor, update its path
#                if self.application.editor.document.path == file_path:
#                    self.application.update_editor_path(new_path)
#            else:
#                context.finish(False, False, timestamp)
#        elif info == self.DND_URI_LIST: # From file manager
#            # Extract paths
#            uris = selection.get_uris()
#            paths = []
#            for uri in uris:
#                if uri.startswith('file://'):
#                    paths.append(urllib.url2pathname(uri[7:]))
#            # Add files
#            for path in paths:
#                if os.path.isfile(path):
#                    self.project.add_file(
#                        path, self.project.files.get_iter(tree_path), position)

# vim:tabstop=4:expandtab
