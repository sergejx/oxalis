# Oxalis -- A website building tool for Gnome
# Copyright (C) 2014 Sergej Chodarev
#
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

import sys
from gi.repository import Gio, GLib, Gtk

import oxalis
from oxalis import main, resources


def init_app():
    GLib.set_application_name("Oxalis")
    app = Gtk.Application.new('sergejx.oxalis', Gio.ApplicationFlags.FLAGS_NONE)
    app.connect('activate', activate_app)
    return app


def setup_menu(app):
    about_action = Gio.SimpleAction.new('about')
    about_action.connect('activate', about_app)
    app.add_action(about_action)

    quit_action = Gio.SimpleAction(name='quit')
    quit_action.connect('activate', lambda a, p: app.quit())
    app.add_action(quit_action)

    app_menu = Gio.Menu.new()
    app_menu.append("About", 'app.about')
    app_menu.append("Quit", 'app.quit')
    app.set_app_menu(app_menu)


def activate_app(app):
    setup_menu(app)
    win = main.MainWindow()
    app.add_window(win.window)
    win.window.show_all()


def about_app(action, param):
    about = Gtk.AboutDialog(version=oxalis.__version__,
                            logo_icon_name=oxalis.__package__,
                            comments=oxalis.__description__,
                            copyright=oxalis.__copyright__,
                            website=oxalis.__url__,
                            license_type=Gtk.License.GPL_2_0,
                            authors=[oxalis.__author__])
    about.run()
    about.destroy()


def run():
    resources.setup_development_paths()
    app = init_app()
    app.run(sys.argv)


if __name__ == '__main__':
    run()
