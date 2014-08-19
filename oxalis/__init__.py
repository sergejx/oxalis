import os
import sys

APP_INFO = {
    'name': "Oxalis",
    'version': "0.3.dev",
    'description': "A website building tool for Gnome",
    'url': 'http://sergejx.mysteria.cz/oxalis/',
    'copyright': "Copyright © 2005-2014 Sergej Chodarev",
}

DATA_DIR = os.path.join(sys.prefix, 'share', 'oxalis')


def resource_path(*path):
    """Get full path to application data file."""
    return os.path.join(DATA_DIR, *path)
