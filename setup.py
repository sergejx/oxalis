#!/usr/bin/env python

from distutils.core import setup

setup(name = 'oxalis',
	version = '0.0.1',
	description = 'Web Editor',
	author = 'Sergej Chodarev',
	author_email = 'sergejx@centrum.sk',
	packages = ['oxalis'],
	scripts = ['scripts/oxalis'],
	data_files=[
		('share/applications', ['data/oxalis.desktop']),
		('share/pixmaps', ['data/oxalis.png']),
		('share/doc/oxalis', ['COPYING'])
	]
)
