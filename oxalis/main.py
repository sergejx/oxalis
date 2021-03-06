# Oxalis -- A website building tool for Gnome
# Copyright (C) 2005-2014 Sergej Chodarev

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
from gi.repository import Gio, GLib, Gtk

from oxalis import files_browser, site, upload, util
from oxalis.config import Configuration
from oxalis.format_conversion import convert_01_to_03
from oxalis.server import PreviewServer
from oxalis.site_settings import SiteSettingsDialog
from oxalis.util import open_browser, open_terminal

XDG_CONFIG_HOME = (os.environ.get("XDG_CONFIG_HOME")
                   or os.path.expanduser("~/.config"))
# Read application configuration
settings = Configuration(os.path.join(XDG_CONFIG_HOME, 'oxalis', 'settings'))


class MainWindow(Gtk.ApplicationWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.connect_after('delete-event', self.on_quit)

        # Create header bar
        self.header = Gtk.HeaderBar(show_close_button=True)
        self.header.set_title("Oxalis")
        self.set_titlebar(self.header)

        # Create main box container
        self.box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        self.add(self.box)

        self.start_panel = StartPanel()
        StartPanelController(self, self.start_panel)
        self.box.pack_start(self.start_panel, True, True, 0)
        self.controller = SiteWindowController(self)

        # Restore window size
        width = settings.getint('state', 'width', fallback=500)
        height = settings.getint('state', 'height', fallback=500)
        self.resize(width, height)

    def add_simple_action(self, name, callback):
        new_file_action = Gio.SimpleAction(name=name)
        new_file_action.connect('activate', callback)
        self.add_action(new_file_action)

    def load_site(self, site, file_browser):
        self.start_panel.destroy()

        self._setup_site_header(site)
        self.box.pack_start(file_browser, True, True, 0)
        file_browser.show_all()

        errors_bar = ErrorsBar(site)
        self.box.pack_start(errors_bar, False, False, 0)

    def _setup_site_header(self, site):
        # Set window title to site name
        self.header.set_title(os.path.basename(site.directory))
        self.header.set_subtitle(os.path.dirname(site.directory))

        # Add "gear" menu
        menu_button = Gtk.MenuButton()
        menu_button.set_menu_model(self._create_menu())
        menu_button.set_image(Gtk.Image.new_from_icon_name(
            'emblem-system-symbolic', Gtk.IconSize.BUTTON))
        self.header.pack_end(menu_button)
        menu_button.show()

        preview_button = Gtk.Button(action_name='win.preview')
        preview_button.set_image(Gtk.Image.new_from_icon_name(
            'web-browser-symbolic', Gtk.IconSize.BUTTON))
        self.header.pack_start(preview_button)
        preview_button.show()

        terminal_button = Gtk.Button(action_name='win.terminal')
        terminal_button.set_image(Gtk.Image.new_from_icon_name(
            'utilities-terminal-symbolic', Gtk.IconSize.BUTTON))
        self.header.pack_start(terminal_button)
        terminal_button.show()

    def _create_menu(self):
        gear_menu = Gio.Menu.new()
        files_menu_section = Gio.Menu()
        files_menu_section.append("New File", 'win.new-file')
        files_menu_section.append("New Directory", 'win.new-directory')
        files_menu_section.append("Add File", 'win.add-file')
        gear_menu.append_section(None, files_menu_section)
        site_menu_section = Gio.Menu()
        site_menu_section.append("Generate", 'win.generate')
        site_menu_section.append("Upload", 'win.upload')
        site_menu_section.append("Site Settings...", 'win.settings')
        gear_menu.append_section(None, site_menu_section)
        return gear_menu

    def on_quit(self, *args):
        width, height = self.get_size()
        settings.setint('state', 'width', width)
        settings.setint('state', 'height', height)
        settings.save()


class StartPanel(Gtk.Alignment):
    """A panel displayed in main window if no site was loaded."""
    def __init__(self):
        super().__init__(xalign=0.5, yalign=0.5, xscale=0.2, yscale=0.0)

        icon = Gtk.Image.new_from_stock(Gtk.STOCK_NEW, Gtk.IconSize.BUTTON)
        self.new_button = Gtk.Button('New site')
        self.new_button.set_image(icon)

        icon = Gtk.Image.new_from_stock(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON)
        self.open_button = Gtk.Button('Open site')
        self.open_button.set_image(icon)

        box = Gtk.VBox()
        box.pack_start(self.new_button, False, False, 0)
        box.pack_start(self.open_button, False, False, 0)
        self.add(box)


class StartPanelController:
    def __init__(self, main_window, start_panel):
        self.window = main_window
        start_panel.new_button.connect('clicked', self.new_site_cb)
        start_panel.open_button.connect('clicked', self.open_site_cb)

    def new_site_cb(self, *args):
        chooser = Gtk.FileChooserDialog(
            'New Site', action=Gtk.FileChooserAction.CREATE_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            'Create', Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        dir_name = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            site.create_site(dir_name)
            self.window.controller.load_site(dir_name)

    def open_site_cb(self, *args):
        chooser = Gtk.FileChooserDialog(
            'Open Site', action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        dir_name = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            site_format = site.check_site_format(dir_name)
            if site_format == '0.3':
                self.window.controller.load_site(dir_name)
            elif site_format == '0.1':
                self.convert_site(dir_name)
            else:
                # Display error message
                message = 'Selected directory is not valid Oxalis site'
                dlg = Gtk.MessageDialog(parent=self.window,
                        type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                        message_format=message)
                dlg.run()
                dlg.destroy()

    def convert_site(self, path):
        """Convert site to new format and load it."""
        message = "Convert selected site to Oxalis 0.3 format?"
        secondary_message = (
            "From version 0.3 Oxalis uses new format of sites. Selected site " +
            "has older format and needs to be converted before opening. " +
            "The conversion preserves all site contents.\n" +
            "Note, however, that after conversion it would not be possible " +
            "to open the site in Oxalis 0.1.")
        dlg = Gtk.MessageDialog(parent=self,
                                type=Gtk.MessageType.QUESTION,
                                message_format=message)
        dlg.format_secondary_text(secondary_message)
        dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        "Convert", Gtk.ResponseType.YES)
        dlg.set_default_response(Gtk.ResponseType.YES)
        response = dlg.run()
        if response == Gtk.ResponseType.YES:
            convert_01_to_03(path)
            self.window.controller.load_site(path)
        dlg.destroy()


class SiteWindowController:
    """
    This object turns main window into a site window with loaded site contents.
    """
    def __init__(self, main):
        self.window = main
        self.site = None
        self.file_browser = None
        self.server = None
        self.settings_dialog = None

    def load_site(self, site_path):
        self.site = site.Site(site_path)

        self._init_actions()
        self.file_browser = files_browser.FilesBrowser(self.window,
                                                       self.site)
        self.window.load_site(self.site, self.file_browser.widget)

        self.server = PreviewServer(self.site)
        self.server.start()

    def _init_actions(self):
        self.window.add_simple_action("new-file", self.on_new_file)
        self.window.add_simple_action("new-directory", self.on_new_directory)
        self.window.add_simple_action('add-file', self.on_add_file)
        self.window.add_simple_action('preview', self.display_preview)
        self.window.add_simple_action('terminal', self.display_terminal)
        self.window.add_simple_action('generate', self.on_generate)
        self.window.add_simple_action('upload', self.on_upload)
        self.window.add_simple_action('settings', self.show_site_settings)

    # Actions handlers #

    def on_new_file(self, action, param):
        response, name = self.ask_name("File")
        if response == Gtk.ResponseType.OK and name != '':
            self.site.new_file(name, self.file_browser.get_target_dir())

    def on_new_directory(self, action, param):
        response, name = self.ask_name("Directory")
        if response == Gtk.ResponseType.OK and name != '':
            self.site.new_directory(name, self.file_browser.get_target_dir())

    def on_add_file(self, action, param):
        chooser = Gtk.FileChooserDialog('Add File', parent=self.window,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK))
        chooser.set_default_response(Gtk.ResponseType.OK)
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.destroy()

        if response == Gtk.ResponseType.OK:
            self.site.add_file(filename, self.file_browser.get_target_dir())

    def ask_name(self, title):
        return util.input_dialog(self.window, "New " + title, "Name:",
                                 "Create")

    def display_preview(self, action, param):
        path = self.site.get_url_path()
        open_browser("http://localhost:%s/%s" % (self.server.port, path))

    def display_terminal(self, action, param):
        path = self.site.directory
        open_terminal(path)

    def on_generate(self, action, param):
        self.site.generate()

    def on_upload(self, action, param):
        dlg = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.QUESTION, 0,
            'Should the site be generated before uploading?')
        dlg.format_secondary_text('''If you made some changes to the site and didn't generate it after that, you should generate it now.''')
        dlg.add_button("Don't generate", Gtk.ResponseType.NO)
        dlg.add_button('Generate', Gtk.ResponseType.YES)
        response = dlg.run()
        dlg.destroy()

        if response == Gtk.ResponseType.YES:
            self.on_generate(None, None)

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
        """Check upload status and move progressbar

        This function is called periodically by gobject timer
        """
        returncode, output = upload.check_upload(process)
        self.upload_output.get_buffer().insert_at_cursor(output)
        if returncode is None:
            self.progress_bar.pulse()
            return True
        else:
            self.progress_bar.set_fraction(1.0)
            self.upload_dlg.set_response_sensitive(Gtk.ResponseType.CLOSE, True)
            return False

    def show_site_settings(self, action, param):
        if self.settings_dialog is None:
            self.settings_dialog = SiteSettingsDialog(self.site,
                                                      self.window)
        self.settings_dialog.run()


class ErrorsBar(Gtk.InfoBar):
    """An info bar displaying error messages for a site."""
    RESPONSE_EDIT = 1
    RESPONSE_SHOW_ALL = 2

    def __init__(self, site):
        super().__init__(message_type=Gtk.MessageType.ERROR, show_close_button=True)
        self.label = Gtk.Label()
        self.get_content_area().add(self.label)
        self.edit_button = self.add_button("Open in Editor", self.RESPONSE_EDIT)
        self.show_button = self.add_button("Show Details", self.RESPONSE_SHOW_ALL)
        self.connect('close', self._on_response)
        self.connect('response', self._on_response)

        self.base_path = site.directory
        self.errors = site.errors
        self.errors.connect('update', self.update_error_messages)

    def update_error_messages(self, errors):
        if len(errors) > 1:
            self.label.set_text("Several errors occurred during conversion.")
            self.show_all()
            self.edit_button.hide()
        elif len(errors) == 1:
            self.label.set_markup(self._format_single_message(errors))
            self.show_all()
            self.show_button.hide()
        else:
            self.hide()

    def show_all_errors(self, errors):
        dialog = Gtk.Dialog("Conversion errors", self.get_toplevel(),
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            ("Close", Gtk.ResponseType.CLOSE),
                            use_header_bar=1)
        dialog.set_default_size(500, 400)
        scrolling = Gtk.ScrolledWindow()
        dialog.get_content_area().add(scrolling)
        label = Gtk.Label()
        label.set_markup(self._format_error_messages(errors))
        scrolling.add_with_viewport(label)
        dialog.show_all()
        dialog.connect('response', lambda dlg, rsp: dlg.destroy())

    def _format_single_message(self, errors):
        error_message = next(iter(errors))
        return "{message} in <i>{file}</i>.".format(**vars(error_message))

    def _format_error_messages(self, errors):
        messages = []
        for error in errors:
            message = "<a href='file://{base_path}/{file}'>{file}</a>: {message}".format(
                base_path=self.base_path, **vars(error))
            messages.append(message)
        return "\n".join(messages)

    def _on_response(self, info_bar, response_id=Gtk.ResponseType.CLOSE):
        if response_id == Gtk.ResponseType.CLOSE:
            info_bar.hide()
        elif response_id == self.RESPONSE_EDIT:
            error = next(iter(self.errors))
            util.open_editor(os.path.join(self.base_path, error.file))
        elif response_id == self.RESPONSE_SHOW_ALL:
            self.show_all_errors(self.errors)
