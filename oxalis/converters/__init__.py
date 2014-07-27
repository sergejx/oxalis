# Oxalis Web Site Editor
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

"""
Converters handle the conversion of source files to targets.

They must implement following methods:

* Constructor (site_path, file_path)
* matches(path) -- tests if the converter can be applied to the file on specified
  path (static method)
* target() -- get a name of generated file
* dependencies() -- a list of paths to file dependencies (change of dependency
  would trigger conversion)
* convert() -- do the conversion
"""

registry = []


def register(clazz):
    """Register a new converter class."""
    registry.append(clazz)
    return clazz


def matching_converter(site_path, path):
    """Return matching converter or None."""
    for converter in registry:
        if converter.matches(path):
            return converter(site_path, path)
    return None