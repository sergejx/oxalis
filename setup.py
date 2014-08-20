#!/usr/bin/env python3
from setuptools import setup

import oxalis

setup(name=oxalis.__package__,
      version=oxalis.__version__,
      description=oxalis.__description__,
      author=oxalis.__author__,
      author_email="sergejx@centrum.sk",
      url=oxalis.__url__,
      packages=['oxalis'],
      scripts=['scripts/oxalis'],
      data_files=[
          ('share/applications', ['data/oxalis.desktop']),
          ('share/icons/hicolor/scalable/apps',
           ['data/icons/hicolor/scalable/apps/oxalis.svg']),
          ('share/icons/hicolor/48x48/apps',
           ['data/icons/hicolor/48x48/apps/oxalis.png']),
          ('share/icons/hicolor/256x256/apps',
           ['data/icons/hicolor/256x256/apps/oxalis.png']),
          ('/usr/share/oxalis/ui', ['data/ui/site-settings.ui']),
          ('share/doc/oxalis', ['COPYING'])
      ],
      requires=['markdown', 'jinja2']
)
