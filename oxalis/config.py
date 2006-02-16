#! /usr/bin/env python

# Oxalis Web Editor
#
# Copyright (C) 2006 Sergej Chodarev
# Based on code from Quod Libet written by Joe Wreschnig 

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

_conffile = os.path.expanduser('~/.oxalis')
_defaults = {
	'window': {
		'width': 600,
		'height': 440,
		'sidepanel-width': 160
	},
	'editor': {
		'font': 'Monospace 10'
	}
}

_config = RawConfigParser()
get = _config.get
getboolean = _config.getboolean
getint = _config.getint
getfloat = _config.getfloat

notifiers = {}


def set(section, key, value):
	_config.set(section, key, value)
	notify(section, key)

def add_notify(section, key, function):
	if (section, key) not in notifiers:
		notifiers[(section, key)] = []
	notifiers[(section, key)].append(function)

def notify(section, key):
	if (section, key) in notifiers:
		for function in notifiers[(section, key)]:
			function()

def write():
	if not os.path.isdir(os.path.dirname(_conffile)):
		os.makedirs(os.path.dirname(_conffile))
	f = file(_conffile, "w")
	_config.write(f)
	f.close()

def init():
	for section, values in _defaults.iteritems():
		_config.add_section(section)
		for key, value in values.iteritems():
			_config.set(section, key, value)
	
	if os.path.exists(_conffile):
		_config.read(_conffile)
