#!/usr/bin/env python3
from setuptools import setup

from oxalis import APP_INFO

setup(name="oxalis",
      version=APP_INFO['version'],
      description=APP_INFO['description'],
      author="Sergej Chodarev",
      author_email="sergejx@centrum.sk",
      url=APP_INFO['url'],
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
          ('share/doc/oxalis', ['COPYING'])
      ],
      requires=['markdown', 'jinja2']
)
