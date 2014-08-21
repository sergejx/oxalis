# Oxalis Web Editor
#
# Copyright (C) 2005-2007 Sergej Chodarev

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
from threading import Thread
import subprocess

from gi.repository import Gtk, GLib

from oxalis import files_browser, site, server, upload, util
from oxalis.config import Configuration
from oxalis.site_settings import SiteSettingsDialog

XDG_CONFIG_HOME = (os.environ.get("XDG_CONFIG_HOME")
                   or os.path.expanduser("~/.config"))
# Read application configuration
settings = Configuration(os.path.join(XDG_CONFIG_HOME, 'oxalis', 'settings'))


ui = '''
<ui>
    <popup action="SiteMenu">
        <menuitem action="NewFile" />
        <menuitem action="NewDirectory" />
        <menuitem action="AddFile" />
        <menuitem action="RenameSelected" />
        <menuitem action="DeleteSelected" />
        <separator />
        <menuitem action="Generate" />
        <menuitem action="Upload" />
        <separator />
        <menuitem action="SiteSettings" />
    </popup>
</ui>
'''


class MainWindow:
    def __init__(self):
        self.window = Gtk.ApplicationWindow()
        self.window.set_title('Oxalis')
        self.window.connect_after('delete-event', self.quit_cb)

        try:
            Gtk.Window.set_default_icon_name('oxalis')
        except GLib.GError:
            print("Warning: Can't load window icon")

        # Create menu bar
        self.ui_manager = Gtk.UIManager()
        accelgroup = self.ui_manager.get_accel_group()
        self.window.add_accel_group(accelgroup)
        self.ui_manager.add_ui_from_string(ui)

        self.site_actions = Gtk.ActionGroup('site_actions')
        self.site_actions.add_actions((
            ('NewFile', None, "New File", None, None, self.on_new_file),
            ('NewDirectory', None, 'New Directory', None, None,
             self.on_new_directory),
            ('AddFile', Gtk.STOCK_ADD, 'Add File', None, None, self.add_file_cb),
            ('Generate', None, 'Generate', None, None, self.generate_cb),
            ('Upload', None, 'Upload', None, None, self.upload_cb),
            ('SiteSettings', None, "Site Settings...", None, None,
                self.show_site_settings)
        ))
        self.site_actions.set_sensitive(False)
        self.selection_actions = Gtk.ActionGroup('selection_actions')
        self.selection_actions.add_actions((
            ('RenameSelected', None, 'Rename selected', None, None,
                self.rename_selected_cb),
            ('DeleteSelected', Gtk.STOCK_DELETE, 'Delete selected', None, None,
                self.delete_selected_cb)
        ))
        self.selection_actions.set_sensitive(False)

        self.ui_manager.insert_action_group(self.site_actions, 0)
        self.ui_manager.insert_action_group(self.selection_actions, 0)

        # Create header bar
        self.header = Gtk.HeaderBar(show_close_button=True)
        self.header.set_title("Oxalis")
        menu_button = Gtk.MenuButton()
        menu_button.set_popup(self.ui_manager.get_widget('/SiteMenu'))
        menu_button.set_image(Gtk.Image.new_from_icon_name(
            'emblem-system-symbolic', Gtk.IconSize.BUTTON))
        self.header.pack_end(menu_button)
        self.window.set_titlebar(self.header)

        self.create_start_panel()

        width = settings.getint('state', 'width', fallback=500)
        height = settings.getint('state', 'height', fallback=500)
        self.window.resize(width, height)

        self.settings_dialog = None

    def create_start_panel(self):
        new = Gtk.Button('New site')
        icon = Gtk.Image.new_from_stock(Gtk.STOCK_NEW, Gtk.IconSize.BUTTON)
        new.set_image(icon)
        new.connect('clicked', self.new_site_cb)

        open = Gtk.Button('Open site')
        icon = Gtk.Image.new_from_stock(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON)
        open.set_image(icon)
        open.connect('clicked', self.open_site_cb)

        box = Gtk.VBox()
        box.pack_start(new, False, False, 0)
        box.pack_start(open, False, False, 0)
        self.start_panel = Gtk.Alignment.new(0.5, 0.5, 0.2, 0.0)
        self.start_panel.add(box)
        self.window.add(self.start_panel)

    def new_site_cb(self, *args):
        chooser = Gtk.FileChooserDialog(
            'New Site', action=Gtk.FileChooserAction.CREATE_FOLDER,
            buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            'Create', Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        dirname = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            site.create_site(dirname)
            self.load_site(dirname)

    def open_site_cb(self, *args):
        chooser = Gtk.FileChooserDialog(
            'Open Site', action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        dirname = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            if site.check_site_format(dirname):
                self.load_site(dirname)
            else:
                # Display error message
                message = 'Selected directory is not valid Oxalis site'
                dlg = Gtk.MessageDialog(parent=self.window,
                    type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                    message_format=message)
                dlg.run()
                dlg.destroy()

    def create_filebrowser(self):
        self.filebrowser = files_browser.FilesBrowser(self, self.site)

    def on_new_file(self, action):
        response, name = self.ask_name("File")
        if response == Gtk.ResponseType.OK and name != '':
            self.site.new_file(name, self.filebrowser.get_target_dir())

    def on_new_directory(self, action):
        response, name = self.ask_name("Label")
        if response == Gtk.ResponseType.OK and name != '':
            self.site.new_directory(name, self.filebrowser.get_target_dir())

    def add_file_cb(self, action):
        chooser = Gtk.FileChooserDialog('Add File', parent=self.window,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            self.site.add_file(filename, self.filebrowser.get_target_dir())

    def rename_selected_cb(self, action):
        '''Rename selected file'''
        obj = self.filebrowser.get_selected_document()

        response, name = util.input_dialog(self.window,
                'Rename', 'Name:', 'Rename', obj.name)

        if type == 'page' and not name.endswith('.html'):
            name += '.html'

        if name != '':
            obj.rename(name)

    def delete_selected_cb(self, action):
        '''Delete selected file, directory or template'''
        obj = self.filebrowser.get_selected_document()

        if isinstance(obj, site.Directory):
            message = ('Delete directory "%(name)s" and its contents?' %
                       {'name': obj.name})
            message2 = 'If you delete the directory, all of its files and its subdirectories will be permanently lost.'
        else:
            message = 'Delete "%(name)s"?' % {'name': obj.name}
            message2 = 'If you delete the item, it will be permanently lost.'

        # Create message dialog
        msg_dlg = Gtk.MessageDialog(parent=self.window,
            type=Gtk.MessageType.WARNING, message_format = message)
        msg_dlg.format_secondary_text(message2)
        msg_dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_DELETE, Gtk.ResponseType.OK)

        msg_dlg.show_all()
        response = msg_dlg.run()
        msg_dlg.destroy()

        if response == Gtk.ResponseType.OK:
            obj.remove()

    def ask_name(self, title):
        return util.input_dialog(self.window, 'New '+title, 'Name:', 'Create')

    def generate_cb(self, action):
        self.site.generate()

    def upload_cb(self, action):
        dlg = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.QUESTION, 0,
            'Should the site be generated before uploading?')
        dlg.format_secondary_text('''If you made some changes to the site and didn't generate it after that, you should generate it now.''')
        dlg.add_button("Don't generate", Gtk.ResponseType.NO)
        dlg.add_button('Generate', Gtk.ResponseType.YES)
        response = dlg.run()
        dlg.destroy()

        if response == Gtk.ResponseType.YES:
            self.generate_cb(None)

        # Start uploading
        process = upload.start_upload(self.site)

        if not process:
            dlg = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, 'Uploading is not configured')
            dlg.run()
            dlg.destroy()
            return

        # Create upload progress dialog
        self.upload_dlg = Gtk.Dialog('Upload', self.window,
            buttons=(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.upload_dlg.set_response_sensitive(Gtk.ResponseType.CLOSE, False)
        self.upload_dlg.set_default_size(500, 310)

        # Box with contents of dialog
        vbox = Gtk.VBox()
        vbox.set_border_width(6)
        vbox.set_spacing(6)

        self.progress_bar = Gtk.ProgressBar()
        vbox.pack_start(self.progress_bar, False, False, 0)

        self.upload_output = Gtk.TextView()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        scrolled.add(self.upload_output)
        vbox.pack_start(scrolled, True, True, 0)

        self.upload_dlg.vbox.pack_start(vbox, True, True, 0)
        self.upload_dlg.show_all()

        GLib.timeout_add(100, self.check_upload, process)

        self.upload_dlg.run()
        self.upload_dlg.destroy()

    def check_upload(self, process):
        '''Check upload status and move progressbar

        This function is called periodically by gobject timer
        '''
        returncode, output = upload.check_upload(process)
        self.upload_output.get_buffer().insert_at_cursor(output)
        if returncode is None:
            self.progress_bar.pulse()
            return True
        else:
            self.progress_bar.set_fraction(1.0)
            self.upload_dlg.set_response_sensitive(Gtk.ResponseType.CLOSE, True)
            return False

    def show_site_settings(self, action):
        if self.settings_dialog is None:
            self.settings_dialog = SiteSettingsDialog(self.site, self.window)
        self.settings_dialog.run()

    def load_site(self, filename):
        self.site = site.Site(filename)

        # Set window title to site name
        self.header.set_title(os.path.basename(filename))
        self.header.set_subtitle(os.path.dirname(filename))

        self.create_filebrowser()

        self.window.remove(self.start_panel)
        self.window.add(self.filebrowser.widget)
        self.filebrowser.widget.show_all()

        self.site_actions.set_sensitive(True)
        self.selection_actions.set_sensitive(False)  # Nothing is selected

        self.start_server()

    def start_server(self):
        server.site = self.site
        server_thread = Thread(target=server.run)
        server_thread.setDaemon(True)
        server_thread.start()

    def load_file(self, doc):
        """Load editor for file.
        doc -- document object for loaded file
        """
        subprocess.Popen(("xdg-open", doc.full_path))

    def quit_cb(self, *args):
        if 'site' in self.__dict__:
            self.site.close()

        width, height = self.window.get_size()
        settings.setint('state', 'width', width)
        settings.setint('state', 'height', height)
        settings.save()
