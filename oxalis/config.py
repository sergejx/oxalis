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

from configparser import ConfigParser, NoSectionError
import os


class Configuration(ConfigParser):
    """ Customized version of ConfigParser. """

    def __init__(self, filename):
        """
        Create configuration object from file (if it exists).
        """
        super().__init__()

        self.filename = filename
        if os.path.exists(self.filename):
            self.read(self.filename)

    def set(self, section, option, value=None):
        """Set option value. If section does not exists, it would be added."""
        try:
            super().set(section, option, value)
        except NoSectionError:
            self.add_section(section)
            super().set(section, option, value)

    def setint(self, section, option, value):
        """Set an integer option value."""
        self.set(section, option, str(value))

    def save(self):
        """Write configuration to file."""
        directory = os.path.dirname(self.filename)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(self.filename, 'w') as file:
            ConfigParser.write(self, file)
