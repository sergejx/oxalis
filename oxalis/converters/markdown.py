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

import os.path
from markdown import Markdown
import jinja2

from oxalis.converters.base import Converter, ErrorMessage

TEMPLATES_DIR = '_templates'


class MarkdownConverter(Converter):
    """
    Converts Markdown files into HTML using templates specified in the header.
    """
    def __init__(self, site_path, path):
        self.path = path
        self.full_path = os.path.join(site_path, path)
        base, ext = os.path.splitext(self.path)
        self.target_path = base + ".html"
        self.full_target_path = os.path.join(site_path, self.target_path)
        self._md = Markdown(extensions=['meta', 'extra'])
        templates_dir = os.path.join(site_path, TEMPLATES_DIR)
        self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir))

    @staticmethod
    def matches(path):
        return path.endswith(".md") or path.endswith(".markdown")

    def target(self):
        return self.target_path

    def dependencies(self):
        return []  # Not implemented

    def _convert_markdown(self, text):
        html = self._md.convert(text)
        context = {'content': html}
        if hasattr(self._md, 'Meta'):
            for key, value in self._md.Meta.items():
                context[key] = "\n".join(value)
        self._md.reset()
        return context

    def convert(self):
        with open(self.full_path) as f:
            text = f.read()
        context = self._convert_markdown(text)
        template_name = context.get("template", "default") + ".html"

        try:
            template = self._env.get_template(template_name)
            full_html = template.render(context)

            with open(self.full_target_path, "w") as f:
                f.write(full_html)

        except jinja2.TemplateNotFound as e:
            return ErrorMessage(self.path, "Template '%s' was not found." % (e.name,))
        except jinja2.TemplateSyntaxError as e:
            return ErrorMessage(os.path.join(TEMPLATES_DIR, e.name),
                                "Template syntax error: %s." % (e.message,))

