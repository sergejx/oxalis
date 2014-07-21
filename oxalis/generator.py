# Oxalis Web Site Editor
#
# Copyright (C) 2005-2011 Sergej Chodarev
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

"""
HTML page generator
~~~~~~~~~~~~~~~~~~~

The module allows to generate HTML page from a text file containing Markdown
formatted text and header with metadata.
"""

import os
import re

import markdown
from .smartypants import smartypants

TAG_RE = re.compile('\{(\w+)\}')


def generate(page):
    """Generates HTML file from Markdown source"""
    tpl = find_template(page)
    if need_to_regenerate(page, tpl):
        f = open(page.target_full_path, 'w')
        f.write(process_page(page))
        f.close()


def need_to_regenerate(page, tpl):
    """
    Check if source file or template was modified after HTML file was
    generated last time.
    """
    if not os.path.exists(page.target_full_path):
        return True
    src_t = os.path.getmtime(page.full_path)
    dst_t = os.path.getmtime(page.target_full_path)
    tpl_t = os.path.getmtime(tpl.full_path) if tpl else 0 # template is optional
    return (src_t > dst_t) or (tpl_t > dst_t)


def process_page(page):
    """Get HTML version of page."""
    html = markdown.markdown(page.read())
    html = smartypants(html)

    html = process_template(page, html)
    encoding = determine_encoding(html)
    return html.encode(encoding)


def find_template(page):
    if 'Template' in page.header and page.header['Template'] != '':
        return page.site.get_document(page.header['Template'], True)
    else:
        return None

def process_template(page, content):
    """Find page template and fill page content into it."""
    tpl = find_template(page)
    if not tpl:
        return content
    tags = page.header.copy()
    tags['Content'] = content
    return fill_template(tpl, tags)

def fill_template(tpl, tags):
    """Fill tags into template."""
    repl = lambda match: replace(match, tags)
    return TAG_RE.sub(repl, tpl.read())

def replace(match, tags):
    tag = match.group(1)
    if tag in tags:
        return tags[tag]
    else:
        return ''

def determine_encoding(html):
    """Determines encoding, in which HTML document should be saved.

    Let's test it with XML declaration
    >>> determine_encoding(
    ...     u'<?xml version="1.0" encoding="iso-8859-2"?>\\n<html></html>')
    'iso-8859-2'

    And what about apostrofs?
    >>> determine_encoding(
    ...     u"<?xml version='1.0' encoding='iso-8859-2'?>\\n<html></html>")
    'iso-8859-2'

    Classical "Content-Type" meta tag:
    >>> determine_encoding(
    ... u'<html><head>\\n<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-2">\\n</head></html>')
    'iso-8859-2'

    HTML5 charset declaration:
    >>> determine_encoding(
    ... u'<html><head>\\n<meta charset="iso-8859-2">\\n</head></html>')
    'iso-8859-2'

    Also without quotes:
    >>> determine_encoding(
    ... u'<html><head>\\n<meta charset=iso-8859-2>\\n</head></html>')
    'iso-8859-2'

    What if we don't specify encoding?
    >>> determine_encoding(
    ... u'<html><head></head><body></body></html>')
    'utf-8'
    """

    re_xml_declaration = re.compile(
        r'<\?xml.*? encoding=(?P<quote>\'|")(?P<enc>.+?)(?P=quote).*?\?>')
    re_meta_charset = re.compile(
        r'<meta.*?charset=[\'"]?(?P<enc>.+?)[\'"> ]',
        re.IGNORECASE)

    match = re_xml_declaration.search(html)
    if match != None:
        return str(match.group('enc'))
    else:
        match = re_meta_charset.search(html)
        if match != None:
            return str(match.group('enc'))
        else:
            return 'utf-8'
