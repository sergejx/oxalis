#!/usr/bin/env python3
import os
from distutils.core import setup
from distutils.command.install_data import install_data

import oxalis


class InstallData(install_data):
    def run(self):
        super().run()
        icon_path = os.path.join(self.install_dir, "share/icons/hicolor")
        self.spawn(["gtk-update-icon-cache", icon_path])


setup(name=oxalis.__package__,
      version=oxalis.__version__,
      description=oxalis.__description__,
      author=oxalis.__author__,
      author_email="sergejx@centrum.sk",
      url=oxalis.__url__,
      packages=['oxalis', 'oxalis.converters'],
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
      cmdclass={'install_data': InstallData})
