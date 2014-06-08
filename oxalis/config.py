# Oxalis Web Editor
#
# Copyright (C) 2006,2008-2009 Sergej Chodarev

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

from configparser import RawConfigParser
import os

XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") \
                  or os.path.expanduser("~/.config")

SETTINGS_DEFAULTS = {
    'state': {
        'width': 800,
        'height': 600,
    },
}

class Configuration(RawConfigParser):
    """
    Configuration system based on ConfigParser with better defaults mechanism
    and with change notification.
    """

    def __init__(self, directory, name, defaults={}):
        """
        Create confituration object from file stored in `directory` and with
        specified `name`.

        If `directory` is set to "$CONFIG" it will be replaced with user
        configuration directory.
        """
        RawConfigParser.__init__(self)
        self.notifiers = {}

        if directory == "$CONFIG":
            self.directory = os.path.join(XDG_CONFIG_HOME, "oxalis")
        else:
            self.directory = directory
        self.name = name
        self.filename = os.path.join(self.directory, name)
        if os.path.exists(self.filename):
            self.read(self.filename)

        # Fill defaults
        for section, values in list(defaults.items()):
            if not self.has_section(section):
                self.add_section(section)
            for key, value in list(values.items()):
                if not self.has_option(section, key):
                    self.set(section, key, value)

    def set(self, section, key, value):
        RawConfigParser.set(self, section, key, value)
        self.notify(section, key)

    def add_notify(self, section, key, function):
        """Add function which would be called after change of the key."""
        if (section, key) not in self.notifiers:
            self.notifiers[(section, key)] = []
        self.notifiers[(section, key)].append(function)

    def notify(self, section, key):
        if (section, key) in self.notifiers:
            for function in self.notifiers[(section, key)]:
                function()

    def write(self):
        """Write configuraion to file."""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        RawConfigParser.write(self, open(self.filename, "w"))

# Read application configuration
settings = Configuration("$CONFIG", "settings", SETTINGS_DEFAULTS)

