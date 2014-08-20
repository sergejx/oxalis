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
from os.path import join, expanduser
import sys

DATA_DIR = join(sys.prefix, 'share', 'oxalis')
XDG_CONFIG_HOME = environ.get('XDG_CONFIG_HOME') or expanduser('~/.config')
CONFIG_DIR = join(XDG_CONFIG_HOME, 'oxalis')


def resource_path(*path):
    """Get full path to application data file."""
    return join(DATA_DIR, *path)


def configuration_path(path):
    """Get full path to user configuration file."""
    return join(CONFIG_DIR, *path)
