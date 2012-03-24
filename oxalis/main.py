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

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import config
import site
import sidepane
import editor
import site_properties
import server
import util
import upload

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
      <menu action="NewFile">
        <menuitem action="NewPage" />
        <menuitem action="NewStyle" />
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
        self.window = gtk.Window()
        self.window.set_title('Oxalis')
        self.window.connect_after('delete-event', self.quit_cb)

        try:
            gtk.window_set_default_icon_from_file('/usr/share/pixmaps/oxalis.png')
        except gobject.GError:
            print "Warning: Can't load window icon"

        # Create menu bar
        self.ui_manager = gtk.UIManager()
        accelgroup = self.ui_manager.get_accel_group()
        self.window.add_accel_group(accelgroup)
        self.ui_manager.add_ui_from_string(ui)

        app_actions = gtk.ActionGroup('app_actions')
        app_actions.add_actions((
            ('SiteMenu', None, 'Site'),
            ('Quit', gtk.STOCK_QUIT, None, None, None, self.quit_cb),
            ('EditMenu', None, 'Edit'),
            ('Preferences', gtk.STOCK_PREFERENCES, None, None, None,
                self.preferences_cb),
            ('HelpMenu', None, 'Help'),
            ('About', gtk.STOCK_ABOUT, None, None, None, self.about_cb)
        ))
        self.site_actions = gtk.ActionGroup('site_actions')
        self.site_actions.add_actions((
            ('NewFile', gtk.STOCK_NEW, 'New File', ''),
            ('NewPage', None, 'Page', None, None, self.new_document_cb),
            ('NewStyle', None, 'Style (CSS)', None, None, self.new_document_cb),
            ('NewDirectory', None, 'Directory', None, None, self.new_document_cb),
            ('NewTemplate', None, 'Template', None, None, self.new_template_cb),
            ('AddFile', gtk.STOCK_ADD, 'Add File', None, None, self.add_file_cb),
            ('Generate', None, 'Generate', None, None, self.generate_cb),
            ('Upload', None, 'Upload', None, None, self.upload_cb),
            ('Properties', gtk.STOCK_PROPERTIES, None, None, None,
                self.properties_cb)
        ))
        self.site_actions.set_sensitive(False)
        self.selection_actions = gtk.ActionGroup('selection_actions')
        self.selection_actions.add_actions((
            ('RenameSelected', None, 'Rename selected', None, None,
                self.rename_selected_cb),
            ('DeleteSelected', gtk.STOCK_DELETE, 'Delete selected', None, None,
                self.delete_selected_cb)
        ))
        self.selection_actions.set_sensitive(False)

        self.ui_manager.insert_action_group(app_actions, 0)
        self.ui_manager.insert_action_group(self.site_actions, 0)
        self.ui_manager.insert_action_group(self.selection_actions, 0)
        menubar = self.ui_manager.get_widget('/MenuBar')

        self.vbox = gtk.VBox()
        self.vbox.pack_start(menubar, False)

        self.create_start_panel()

        self.window.add(self.vbox)

        width = config.settings.getint('state', 'width')
        height = config.settings.getint('state', 'height')
        self.window.resize(width, height)


        config.settings.add_notify('editor', 'font', self.font_changed)

    def create_start_panel(self):
        new = gtk.Button('New site')
        icon = gtk.image_new_from_stock(gtk.STOCK_NEW, gtk.ICON_SIZE_BUTTON)
        new.set_image(icon)
        new.connect('clicked', self.new_site_cb)

        open = gtk.Button('Open site')
        icon = gtk.image_new_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_BUTTON)
        open.set_image(icon)
        open.connect('clicked', self.open_site_cb)

        box = gtk.VBox()
        box.pack_start(new)
        box.pack_start(open)
        self.start_panel = gtk.Alignment(0.5, 0.5, 0.2, 0.0)
        self.start_panel.add(box)
        self.vbox.pack_start(self.start_panel)

    def new_site_cb(self, *args):
        chooser = gtk.FileChooserDialog(
            'New Site', action=gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            'Create', gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        response = chooser.run()
        dirname = chooser.get_filename()
        chooser.destroy()

        if response == gtk.RESPONSE_OK:
            site.create_site(dirname)
            self.load_site(dirname)

    def open_site_cb(self, *args):
        chooser = gtk.FileChooserDialog(
            'Open Site', action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        response = chooser.run()
        dirname = chooser.get_filename()
        chooser.destroy()

        if response == gtk.RESPONSE_OK:
            if site.dir_is_site(dirname):
                self.load_site(dirname)
            else:
                # Display error message
                message = 'Selected directory is not valid Oxalis site'
                dlg = gtk.MessageDialog(parent=self.window,
                    type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                    message_format=message)
                dlg.run()
                dlg.destroy()

    def create_paned(self):
        self.sidepane = sidepane.SidePane(self, self.site)
        self.paned = gtk.HPaned()
        self.paned.add1(self.sidepane)
        self.paned.set_position(
                config.settings.getint('state', 'sidepanel-width'))

    def font_changed(self):
        try:
            self.editor.set_font()
        except AttributeError: # there is no editor
            pass

    NEW_DOC_DATA = {
        "NewPage": (site.PAGE, u"Page", ".html"),
        "NewStyle": (site.STYLE, u"Style", ".css"),
        "NewDirectory": (site.DIRECTORY, u"Directory", ""),
    }
    def new_document_cb(self, action):
        type, label, ext = self.NEW_DOC_DATA[action.get_name()]
        response, name = self.ask_name(label)
        if response == gtk.RESPONSE_OK and name != '':
            if not name.endswith(ext):
                name += ext
            self.site.new_file(type, name, self.sidepane.get_target_dir())

    def new_template_cb(self, action):
        response, name = self.ask_name('Template')

        if response == gtk.RESPONSE_OK:
            if name != '':
                self.site.new_template(name)

    def add_file_cb(self, action):
        chooser = gtk.FileChooserDialog('Add File', parent=self.window,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.destroy()

        if response == gtk.RESPONSE_OK:
            self.site.add_file(filename, self.sidepane.get_target_dir())

    def rename_selected_cb(self, action):
        '''Rename selected file'''
        obj = self.sidepane.get_selected_document()

        response, name = util.input_dialog(self.window,
                'Rename', 'Name:', 'Rename', obj.name)

        if type == 'page' and not name.endswith('.html'):
            name += '.html'

        if name != '':
            new_path = obj.rename(name)

        # If renamed file is opened in editor, update its path
        if self.editor.document == obj:
            self.update_editor_path(new_path)

    def delete_selected_cb(self, action):
        '''Delete selected file, directory or template'''
        obj = self.sidepane.get_selected_document()

        if isinstance(obj, site.Directory):
            message = ('Delete directory "%(name)s" and its contents?' %
                       {'name': obj.name})
            message2 = 'If you delete the directory, all of its files and its subdirectories will be permanently lost.'
        else:
            message = 'Delete "%(name)s"?' % {'name': obj.name}
            message2 = 'If you delete the item, it will be permanently lost.'

        # Create message dialog
        msg_dlg = gtk.MessageDialog(parent=self.window,
            type=gtk.MESSAGE_WARNING, message_format = message)
        msg_dlg.format_secondary_text(message2)
        msg_dlg.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_DELETE, gtk.RESPONSE_OK)

        msg_dlg.show_all()
        response = msg_dlg.run()
        msg_dlg.destroy()

        if response == gtk.RESPONSE_OK:
            # If removed file is opened in editor, replace it with DummyEditor
            if self.editor.document == obj:
                self.load_file(None)
            obj.remove()

    def ask_name(self, title):
        return util.input_dialog(self.window, 'New '+title, 'Name:', 'Create')

    def generate_cb(self, action):
        self.editor.save()
        self.site.generate()

    def upload_cb(self, action):
        dlg = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_QUESTION, 0,
            'Should the site be generated before uploading?')
        dlg.format_secondary_text('''If you made some changes to the site and didn't generate it after that, you should generate it now.''')
        dlg.add_button("Don't generate", gtk.RESPONSE_NO)
        dlg.add_button('Generate', gtk.RESPONSE_YES)
        response = dlg.run()
        dlg.destroy()

        if response == gtk.RESPONSE_YES:
            self.generate_cb(None)

        # Start uploading
        process = upload.start_upload(self.site)

        if not process:
            dlg = gtk.MessageDialog(self.window, 0, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_OK, 'Uploading is not configured')
            dlg.run()
            dlg.destroy()
            return

        # Create upload progress dialog
        self.upload_dlg = gtk.Dialog('Upload', self.window,
            gtk.DIALOG_NO_SEPARATOR, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.upload_dlg.set_response_sensitive(gtk.RESPONSE_CLOSE, False)
        self.upload_dlg.set_default_size(500, 310)

        # Box with contents of dialog
        vbox = gtk.VBox()
        vbox.set_border_width(6)
        vbox.set_spacing(6)

        self.progress_bar = gtk.ProgressBar()
        vbox.pack_start(self.progress_bar, False)

        self.upload_output = gtk.TextView()
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        scrolled.add(self.upload_output)
        vbox.pack_start(scrolled)

        self.upload_dlg.vbox.pack_start(vbox)
        self.upload_dlg.show_all()

        gobject.timeout_add(100, self.check_upload, process)

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
            self.upload_dlg.set_response_sensitive(gtk.RESPONSE_CLOSE, True)
            return False

    def properties_cb(self, action):
        site_properties.properties_dialog(self.site, self.window)

    def load_site(self, filename):
        self.site = site.Site(filename)

        self.create_paned()

        last_file = self.site.config.get('state', 'last_document')
        last_file_type = self.site.config.get('state', 'last_document_type')

        self.vbox.remove(self.start_panel)
        self.vbox.pack_start(self.paned)
        self.paned.show_all()

        self.site_actions.set_sensitive(True)
        self.selection_actions.set_sensitive(False)  # Nothing is selected

        doc = self.site.get_document(last_file,
                                        last_file_type == 'template')
        self.load_file(doc)

        self.start_server()

    def start_server(self):
        server.site = self.site
        server_thread = Thread(target=server.run)
        server_thread.setDaemon(True)
        server_thread.start()

    def load_file(self, doc):
        """Load editor for file.

        doc -- document object for loaded file

        If there is already opened editor, it will be unloaded.
        """
        try:
            # Get new editor
            if doc is not None:
                new_editor = editor.create_editor(doc)
            else:
                new_editor = editor.DummyEditor()

            # Unload old editor
            if 'editor' in self.__dict__:
                self.editor.save()
                self.paned.remove(self.editor)
                # Remove editor UI and actions
                #self.ui_manager.remove_ui(self.editor_merge_id)
                #self.ui_manager.remove_action_group(self.editor.edit_actions)

            # Load new one
            self.editor = new_editor
            self.paned.add2(self.editor)
            self.editor.show_all()

            # Add editor UI and actions (commented out because of issue gh-1)
            #ui = self.editor.ui
            #actions = self.editor.edit_actions
            #self.editor_merge_id = self.ui_manager.add_ui_from_string(ui)
            #self.ui_manager.insert_action_group(actions, 1)
        except editor.NoEditorException:
            pass # Documend does not provide editor

    def update_editor_path(self, new_path):
        '''Update path of document which is opened in active editor'''
        self.editor.document.path = new_path
        self.editor.set_editor_label()

    def run(self):
        self.make_window()
        self.window.show_all()
        gtk.gdk.threads_init()
        gtk.main()

    def preferences_cb(self, action):
        pref = PreferencesDialog(self.window)
        pref.run()
        pref.destroy()

    def about_cb(self, action):
        gtk.about_dialog_set_url_hook(open_url)
        about = gtk.AboutDialog()
        about.set_name(NAME)
        about.set_version(VERSION)
        about.set_comments(COMMENTS)
        about.set_copyright(COPYRIGHT)
        about.set_website(WEBSITE)
        about.set_authors(AUTHORS)
        about.run()
        about.destroy()

    def quit_cb(self, *args):
        if 'editor' in self.__dict__:
            self.editor.save()
            self.site.config.set('state', 'last_document',
                    self.editor.document.path)
            if isinstance(self.editor, editor.TemplateEditor):
                file_type = 'template'
            else:
                file_type = 'file'
            self.site.config.set('state', 'last_document_type', file_type)
        if 'site' in self.__dict__:
            self.site.close()

        width, height = self.window.get_size()
        config.settings.set('state', 'width', width)
        config.settings.set('state', 'height', height)
        if 'paned' in self.__dict__:
            config.settings.set('state', 'sidepanel-width',
                                self.paned.get_position())
        config.settings.write()
        gtk.main_quit()


class PreferencesDialog(gtk.Dialog):
    def __init__(self, parent):
        buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        gtk.Dialog.__init__(self, 'Oxalis Preferences', parent,
                            buttons=buttons)
        label = gtk.Label('Editor font:')
        font_button = gtk.FontButton(config.settings.get('editor', 'font'))
        font_button.connect('font-set', self.font_set)
        box = gtk.HBox()
        box.pack_start(label, False, False, 6)
        box.pack_start(font_button, True, True, 6)
        self.vbox.pack_start(box, True, True, 6)
        self.show_all()

    def font_set(self, font_button):
        config.settings.set('editor', 'font', font_button.get_font_name())


def open_url(dialog, link):
    subprocess.call(('gnome-open', link))


def run():
    Oxalis().run()

