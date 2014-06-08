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

from threading import Thread
import subprocess

from gi.repository import Gtk, GLib, Gdk

from . import config
from . import site
from . import sidepane
from . import site_properties
from . import server
from . import util
from . import upload

NAME = 'Oxalis'
VERSION = '0.1'
COMMENTS = 'Web Site Editor'
COPYRIGHT = 'Copyright \302\251 2005-2006 Sergej Chodarev'
WEBSITE = 'http://sergejx.mysteria.cz/oxalis/'
AUTHORS = ('Sergej Chodarev',
    '',
    'Oxalis includes:',
    '* smartypants.py by Chad Miller',
    'Author of original Markdown and SmartyPants is John Gruber'
)

ui = '''
<ui>
  <menubar name="MenuBar">
    <menu action="SiteMenu">
      <menu action="New">
        <menuitem action="NewPage" />
        <menuitem action="NewHtml" />
        <menuitem action="NewStyle" />
        <menuitem action="NewFile" />
        <menuitem action="NewDirectory" />
        <menuitem action="NewTemplate" />
      </menu>
      <menuitem action="AddFile" />
      <menuitem action="RenameSelected" />
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
    def make_window(self):
        self.window = Gtk.Window()
        self.window.set_title('Oxalis')
        self.window.connect_after('delete-event', self.quit_cb)

        try:
            Gtk.Window.set_default_icon_from_file('/usr/share/pixmaps/oxalis.png')
        except GLib.GError:
            print("Warning: Can't load window icon")

        # Create menu bar
        self.ui_manager = Gtk.UIManager()
        accelgroup = self.ui_manager.get_accel_group()
        self.window.add_accel_group(accelgroup)
        self.ui_manager.add_ui_from_string(ui)

        app_actions = Gtk.ActionGroup('app_actions')
        app_actions.add_actions((
            ('SiteMenu', None, 'Site'),
            ('Quit', Gtk.STOCK_QUIT, None, None, None, self.quit_cb),
            ('EditMenu', None, 'Edit'),
            ('Preferences', Gtk.STOCK_PREFERENCES, None, None, None,
                self.preferences_cb),
            ('HelpMenu', None, 'Help'),
            ('About', Gtk.STOCK_ABOUT, None, None, None, self.about_cb)
        ))
        self.site_actions = Gtk.ActionGroup('site_actions')
        self.site_actions.add_actions((
            ('New', Gtk.STOCK_NEW, "New", ''),
            ('NewPage', None, "Markdown Page", None, None,
                self.new_document_cb),
            ('NewHtml', None, "HTML Page", None, None, self.new_document_cb),
            ('NewStyle', None, "CSS Style", None, None, self.new_document_cb),
            ('NewFile', None, "File", None, None, self.new_document_cb),
            ('NewDirectory', None, 'Directory', None, None, self.new_document_cb),
            ('NewTemplate', None, 'Template', None, None, self.new_template_cb),
            ('AddFile', Gtk.STOCK_ADD, 'Add File', None, None, self.add_file_cb),
            ('Generate', None, 'Generate', None, None, self.generate_cb),
            ('Upload', None, 'Upload', None, None, self.upload_cb),
            ('Properties', Gtk.STOCK_PROPERTIES, None, None, None,
                self.properties_cb)
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

        self.ui_manager.insert_action_group(app_actions, 0)
        self.ui_manager.insert_action_group(self.site_actions, 0)
        self.ui_manager.insert_action_group(self.selection_actions, 0)
        menubar = self.ui_manager.get_widget('/MenuBar')

        self.vbox = Gtk.VBox()
        self.vbox.pack_start(menubar, False, False, 0)

        self.create_start_panel()

        self.window.add(self.vbox)

        width = config.settings.getint('state', 'width')
        height = config.settings.getint('state', 'height')
        self.window.resize(width, height)


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
        self.vbox.pack_start(self.start_panel, True, True, 0)

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
            if site.dir_is_site(dirname):
                self.load_site(dirname)
            else:
                # Display error message
                message = 'Selected directory is not valid Oxalis site'
                dlg = Gtk.MessageDialog(parent=self.window,
                    type=Gtk.MessageType.ERROR, buttons=Gtk.BUTTONS_OK,
                    message_format=message)
                dlg.run()
                dlg.destroy()

    def create_filebrowser(self):
        self.filebrowser = sidepane.SidePane(self, self.site)

    NEW_DOC_DATA = {
        'NewPage': (site.PAGE, "Markdown Page", ".text"),
        'NewHtml': (site.FILE, "HTML Page", ".html"),
        "NewStyle": (site.STYLE, "Style", ".css"),
        'NewFile': (site.FILE, "File", ""),
        "NewDirectory": (site.DIRECTORY, "Directory", ""),
    }

    def new_document_cb(self, action):
        type, label, ext = self.NEW_DOC_DATA[action.get_name()]
        response, name = self.ask_name(label)
        if response == Gtk.ResponseType.OK and name != '':
            if not name.endswith(ext):
                name += ext
            self.site.new_file(type, name, self.filebrowser.get_target_dir())

    def new_template_cb(self, action):
        response, name = self.ask_name('Template')

        if response == Gtk.ResponseType.OK:
            if name != '':
                self.site.new_template(name)

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
                Gtk.BUTTONS_OK, 'Uploading is not configured')
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

    def properties_cb(self, action):
        site_properties.properties_dialog(self.site, self.window)

    def load_site(self, filename):
        self.site = site.Site(filename)

        self.create_filebrowser()

        self.vbox.remove(self.start_panel)
        self.vbox.pack_start(self.filebrowser, True, True, 0)
        self.filebrowser.show_all()

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

    def run(self):
        self.make_window()
        self.window.show_all()
        Gdk.threads_init()
        Gtk.main()

    def preferences_cb(self, action):
        pref = PreferencesDialog(self.window)
        pref.run()
        pref.destroy()

    def about_cb(self, action):
        about = Gtk.AboutDialog()
        about.set_name(NAME)
        about.set_version(VERSION)
        about.set_comments(COMMENTS)
        about.set_copyright(COPYRIGHT)
        about.set_website(WEBSITE)
        about.set_authors(AUTHORS)
        about.run()
        about.destroy()

    def quit_cb(self, *args):
        if 'site' in self.__dict__:
            self.site.close()

        width, height = self.window.get_size()
        config.settings.set('state', 'width', width)
        config.settings.set('state', 'height', height)
        config.settings.write()
        Gtk.main_quit()


class PreferencesDialog(Gtk.Dialog):
    def __init__(self, parent):
        buttons = (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        Gtk.Dialog.__init__(self, 'Oxalis Preferences', parent,
                            buttons=buttons)
        self.show_all()


def run():
    Oxalis().run()

