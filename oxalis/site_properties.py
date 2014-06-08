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

import util

from gi.repository import Gtk

def properties_dialog(site, parent_window):
    """Display site properties dialog."""
    settings = {}
    settings['upload'] = dict(site.config.items('upload'))
    settings['preview'] = dict(site.config.items('preview'))
    dialog = SitePropertiesDialog(parent_window, settings)
    response = dialog.run()
    settings = dialog.get_settings()
    dialog.destroy()

    if response == Gtk.ResponseType.OK:
        for section in settings:
            for key, value in settings[section].items():
                site.config.set(section, key, value)
        # Save properties
        site.config.write()

class SitePropertiesDialog(Gtk.Dialog):
    """Dialog for editing site properties."""

    keys = ('host', 'user', 'passwd', 'remotedir')
    texts = {
        'host': "Host:",
        'user': "User:",
        'passwd': "Password:",
        'remotedir': "Remote Directory:",
    }

    def __init__(self, window = None, settings = {}):
        Gtk.Dialog.__init__(self, 'Site Properties', window,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)

        # Upload settings
        self.entries = {}
        table_rows = []
        for key in self.keys:
            self.entries[key] = Gtk.Entry()
            if key in settings['upload']:
                self.entries[key].set_text(settings['upload'][key])
            table_rows.append((self.texts[key], self.entries[key]))
        self.entries['passwd'].set_visibility(False)

        table = util.make_table(table_rows)
        table.set_row_spacings(6)
        table.set_col_spacings(12)

        # Preview settings
        vbox = Gtk.VBox()
        vbox.set_spacing(6)

        hbox = Gtk.HBox()
        hbox.set_spacing(12)
        hbox.pack_start(Gtk.Label('Path in URL:'), False, False, 0)
        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(settings['preview']['url_path'])
        hbox.pack_start(self.path_entry, True, True, 0)
        vbox.pack_start(hbox, True, True, 0)
        description = Gtk.Label()
        description.set_markup(
            '<small>This setting is used for resolving absolute paths in previews. '
            'For example if your site will be accessible via adress '
            '<tt>http://www.example.com/mysite/</tt> enter <tt>mysite</tt></small>')
        description.set_line_wrap(True)
        description.set_alignment(0, 0.5)
        vbox.pack_start(description, True, True, 0)

        # Pack everything
        box = util.make_dialog_layout((
            ('Upload settings', table),
            ('Preview settings', vbox)
        ))

        self.vbox.pack_start(box, True, True, 0)
        self.vbox.show_all()

    def get_settings(self):
        settings = {}
        settings['upload'] = {}
        for key in self.keys:
            settings['upload'][key] = self.entries[key].get_text()
        settings['preview'] = {}
        settings['preview']['url_path'] = self.path_entry.get_text()
        return settings

