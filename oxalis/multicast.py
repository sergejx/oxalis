"""
Simple method multicasting.
"""
# Copyright (C) 2005-2011 Sergej Chodarev
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

class Multicaster(object):
    """
    Method call multicaster.

    Multicaster object maintains a set of listeners. If a method is called on
    multicaster, it is called on all listeners which define such method.
    """
    def __init__(self):
        self._listeners = set()

    def __iadd__(self, other):
        """Add listener of multicast messages (+= operator)."""
        self._listeners.add(other)

    def __getattr__(self, name):
        """For any requested attribute just return multicasting_method."""
        def multicasting_method(*args, **kwargs):
            """Call method on all listeners which implement it."""
            for listener in self._listeners:
                try:
                    getattr(listener, name)(*args, **kwargs)
                except Exception as e:
                    # we don't care about exceptions
                    print e
        return multicasting_method
