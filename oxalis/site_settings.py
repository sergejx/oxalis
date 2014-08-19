# Oxalis - A website building tool for Gnome
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

import oxalis


class SiteSettingsDialog:
    """Dialog for editing site settings."""

    entries_to_settings = {
        'preview_url': ('preview', 'url_path'),
        'upload_host': ('upload', 'host'),
        'upload_user': ('upload', 'user'),
        'upload_password': ('upload', 'passwd'),
        'upload_dir': ('upload', 'remotedir')
    }

    def __init__(self, site,  window):
        self.site = site

        builder = Gtk.Builder()
        builder.add_objects_from_file(
            oxalis.resource_path('ui', 'site-settings.ui'),
            ('site-settings-box',))
        self.dialog = Gtk.Dialog(title="Site Settings", parent=window,
                                 use_header_bar=1)
        self.dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        self.dialog.set_default_response(Gtk.ResponseType.OK)
        box = builder.get_object('site-settings-box')
        self.dialog.get_content_area().add(box)

        self.entries = {}
        for entry in self.entries_to_settings.keys():
            self.entries[entry] = builder.get_object(entry)

    def run(self):
        """Run dialog and save user modifications of settings."""
        self.fill_settings(self.site.config)
        self.dialog.show_all()
        response = self.dialog.run()
        if response == Gtk.ResponseType.OK:
            self.save_settings(self.site.config)
            self.site.config.save()
        self.dialog.hide()

    def fill_settings(self, settings):
        for entry, (section, option) in self.entries_to_settings.items():
            value = settings.get(section, option, fallback="")
            self.entries[entry].set_text(value)

    def save_settings(self, settings):
        for entry, (section, option) in self.entries_to_settings.items():
            if section not in settings:
                settings[section] = {}
            settings[section][option] = self.entries[entry].get_text()
