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

def make_table(rows):
    '''Create Gtk.Table for controls and their labels

    rows - sequence of rows. Each of rows is tuple with 2 items:
        label text and control widget
    '''
    height = len(rows)
    table = Gtk.Table(height, 2)
    i = 0
    for row in rows:
        label = Gtk.Label(row[0])
        label.set_alignment(0, 0.5)
        table.attach(label, 0, 1, i, i+1, Gtk.AttachOptions.FILL, 0)
        table.attach(row[1], 1, 2, i, i+1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 0)
        i += 1
    return table

def make_dialog_layout(groups):
    '''Create Gtk.VBox for dialog windows with groups of controls properly
    indented.

    groups - sequence of groups of contollers. Each item of sequence contain
        2 items: group label text and group controllers
    '''

    vbox = Gtk.VBox()
    vbox.set_border_width(6)
    vbox.set_spacing(18)

    for group in groups:
        group_box = Gtk.VBox()
        group_box.set_spacing(6)
        label = Gtk.Label()
        label.set_markup('<b>%s</b>' % group[0])
        label.set_alignment(0, 0.5)
        group_box.pack_start(label, True, True, 0)

        alignment = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        alignment.add(group[1])
        alignment.set_padding(0, 0, 12, 0)
        group_box.pack_start(alignment, True, True, 0)

        vbox.pack_start(group_box, True, True, 0)
    return vbox

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

# vim:tabstop=4:expandtab
