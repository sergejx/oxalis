# Oxalis Web Editor
# Utility functions
#
# Copyright (C) 2005-2006 Sergej Chodarev

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
import subprocess


def open_editor(path):
    """Open editor for a file."""
    subprocess.Popen(("xdg-open", path))


def open_browser(url):
    """Open web browser for a URL."""
    subprocess.Popen(("xdg-open", url))


def open_terminal(path):
    """Open terminal emulator in a path."""
    # TODO: Detect default terminal, or make it configurable?
    subprocess.Popen(("gnome-terminal", "--working-directory=" + path))


def input_dialog(parent, title, label, ok_label, value=''):
    '''Show dialog asking user for input

    parent - parent window
    title - title of dialog
    label - label for text entry
    ok_label - label for OK button
    value - default value of text entry

    Returns tuple: response code, value of text entry
    '''
    buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, ok_label, Gtk.ResponseType.OK)
    dialog = Gtk.Dialog(parent=parent, title=title, buttons=buttons)
    dialog.set_default_response(Gtk.ResponseType.OK)

    label = Gtk.Label(label)
    entry = Gtk.Entry()
    entry.set_text(value)
    entry.set_activates_default(True)
    hbox = Gtk.HBox()
    hbox.pack_start(label, False, False, 6)
    hbox.pack_start(entry, True, True, 6)
    dialog.vbox.pack_start(hbox, True, True, 6)
    hbox.show_all()

    response = dialog.run()
    value = entry.get_text()
    dialog.destroy()
    return response, value
