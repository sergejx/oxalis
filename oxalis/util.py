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

import gtk

def make_table(rows):
	'''Create gtk.Table for controls and their labels
	
	rows - sequence of rows. Each of rows is tuple with 2 items:
		label text and control widget
	'''
	height = len(rows)
	table = gtk.Table(height, 2)
	i = 0
	for row in rows:
		label = gtk.Label(row[0])
		label.set_alignment(0, 0.5)
		table.attach(label, 0, 1, i, i+1, gtk.FILL, 0)
		table.attach(row[1], 1, 2, i, i+1, gtk.EXPAND|gtk.FILL, 0)
		i += 1
	return table
