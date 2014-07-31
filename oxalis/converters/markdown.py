# Oxalis Web Site Editor
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

import os.path

from markdown import Markdown
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = '_templates'


class MarkdownConverter:
    """
    Converts Markdown files into HTML using templates specified in the header.
    """
    def __init__(self, site_path, path):
        self.path = path
        self.full_path = os.path.join(site_path, path)
        base, ext = os.path.splitext(self.path)
        self.target_path = base + ".html"
        self.full_target_path = os.path.join(site_path, self.target_path)
        self._md = Markdown(extensions=['meta'])
        templates_dir = os.path.join(site_path, TEMPLATES_DIR)
        self._env = Environment(loader=FileSystemLoader(templates_dir))

    @staticmethod
    def matches(path):
        return path.endswith(".md") or path.endswith(".markdown")

    def target(self):
        return self.target_path

    def dependencies(self):
        return []  # Not implemented

    def convert(self):
        with open(self.full_path) as f:
            text = f.read()
        html = self._md.convert(text)
        meta = self._md.Meta
        template_name = meta.get("template", ["default"])[0] + ".html"
        template = self._env.get_template(template_name)
        context = dict(meta)
        context['content'] = html
        full_html = template.render(context)
        with open(self.full_target_path, "w") as f:
            f.write(full_html)
        self._md.reset()  # Reset Markdown