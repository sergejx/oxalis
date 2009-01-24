# Oxalis Web Editor
#
# Copyright (C) 2006,2008 Sergej Chodarev

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

from ConfigParser import RawConfigParser
import os

XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") \
                  or os.path.expanduser("~/.config")

SETTINGS_DEFAULTS = {
    'font': 'Monospace 10',
}

STATE_DEFAULTS = {
    'width': 800,
    'height': 600,
    'sidepanel-width': 160,
}

class Configuration(object):
    """
    Simple configuration system based on ConfigParser but without sections and
    with change notification.
    """

    def __init__(self, directory, name, defaults={}):
        """
        Create confituration object from file stored in `directory` and with
        specified `name`.

        If `directory` is set to "$CONFIG" it will be replaced with user
        configuration directory.
        """
        self.config = RawConfigParser(defaults)
        if directory == "$CONFIG":
            self.directory = os.path.join(XDG_CONFIG_HOME, "oxalis")
        else:
            self.directory = directory
        self.name = name
        self.filename = os.path.join(self.directory, name + ".cfg")
        if os.path.exists(self.filename):
            self.config.read(self.filename)
        if not self.config.has_section(self.name):
            self.config.add_section(self.name)
        self.notifiers = {}

    def set(self, key, value):
        self.config.set(self.name, key, value)
        self.notify(key)

    def get(self, key):
        return self.config.get(self.name, key)

    def getint(self, key):
        return self.config.getint(self.name, key)

    def has_option(self, key):
        return self.config.has_option(self.name, key)

    def items(self):
        return self.config.items(self.name)

    def add_notify(self, key, function):
        """Add function which would be called after change of the key."""
        if key not in self.notifiers:
            self.notifiers[key] = []
        self.notifiers[key].append(function)

    def notify(self, key):
        if key in self.notifiers:
            for function in self.notifiers[key]:
                function()

    def write(self):
        """Write configuraion to file."""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.config.write(file(self.filename, "w"))

# Read application configuration
settings = Configuration("$CONFIG", "settings", SETTINGS_DEFAULTS)
state = Configuration("$CONFIG", "state", STATE_DEFAULTS)

