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

from os import environ
from os.path import abspath, dirname, join
import sys

from gi.repository import GLib


DATA_DIR = join(sys.prefix, 'share', 'oxalis')
CONFIG_DIR = join(GLib.get_user_config_dir(), 'oxalis')


def resource_path(*path):
    """Get full path to application data file."""
    return join(DATA_DIR, *path)


def configuration_path(path):
    """Get full path to user configuration file."""
    return join(CONFIG_DIR, *path)


def setup_development_paths():
    """Setup paths to resources for cases when application is not installed."""
    global DATA_DIR
    if not __file__.startswith(sys.prefix):  # Running without installation
        # Set data directory
        DATA_DIR = abspath(
            join(dirname(__file__), '..', 'data'))
        # Also alter XDG_DATA_DIR
        xdg_data_dirs = environ.get('XDG_DATA_DIRS', '/usr/share/')
        environ['XDG_DATA_DIRS'] = DATA_DIR + ':' + xdg_data_dirs
