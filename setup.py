#!/usr/bin/env python

from distutils.core import setup

setup(name = 'oxalis',
	version = '0.1-alpha4',
	description = 'Web Site Editor',
	author = 'Sergej Chodarev',
	author_email = 'sergejx@centrum.sk',
	url='http://sergejx.mysteria.cz/oxalis/',
	packages = ['oxalis'],
	scripts = ['scripts/oxalis'],
	data_files=[
		('share/applications', ['data/oxalis.desktop']),
		('share/pixmaps', ['data/oxalis.png']),
		('share/doc/oxalis', ['COPYING'])
	]
)
