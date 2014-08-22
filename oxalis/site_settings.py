# Oxalis -- A website building tool for Gnome
# Copyright (C) 2014 Sergej Chodarev
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

from oxalis.resources import resource_path


class SiteSettingsDialog:
    """Dialog for editing site settings."""

    upload_entries = {  # entry ID: configuration key
        'upload_host': 'host',
        'upload_user': 'user',
        'upload_password': 'passwd',
        'upload_dir': 'remotedir'
    }

    def __init__(self, site,  window):
        self.site = site

        builder = Gtk.Builder()
        builder.add_objects_from_file(resource_path('ui', 'site-settings.ui'),
                                      ['site-settings-box'])
        self.dialog = Gtk.Dialog(title="Site Settings", parent=window,
                                 use_header_bar=1)
        self.dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        box = builder.get_object('site-settings-box')
        self.dialog.get_content_area().add(box)

        self.preview_url_entry = builder.get_object('preview_url')
        self.entries = {}
        for entry in self.upload_entries.keys():
            self.entries[entry] = builder.get_object(entry)

    def run(self):
        """Run dialog and save user modifications of settings."""
        self.fill_settings(self.site)
        self.dialog.show_all()
        response = self.dialog.run()
        if response == Gtk.ResponseType.OK:
            self.save_settings(self.site)
            self.site.config.save()
        self.dialog.hide()

    def fill_settings(self, site):
        self.preview_url_entry.set_text(
            site.config.get('preview', 'url_path', fallback=''))
        for entry, option in self.upload_entries.items():
            value = site.upload_config.get('upload', option, fallback="")
            self.entries[entry].set_text(value)

    def save_settings(self, site):
        site.config.set('preview', 'url_path', self.preview_url_entry.get_text())
        for entry, option in self.upload_entries.items():
            site.upload_config.set('upload', option,
                                   self.entries[entry].get_text())
