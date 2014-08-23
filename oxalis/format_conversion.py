"""Conversion of old Oxalis site format to the new one."""

import os
from os.path import join
import re

from oxalis.config import Configuration
from oxalis.site import TEMPLATES_DIR


def convert_01_to_03(path):
    """Convert site from old format (0.1) to the new one (0.3)."""
    _split_upload_config(path)
    _rename_text_to_md(path)
    _move_templates_to_root(path)
    _convert_templates_to_jinja(path)
    _change_format_version(path, '0.3')


def _split_upload_config(path):
    """Move upload configuration into separate file."""
    config = Configuration(join(path, '_oxalis', 'config'))
    upload_section = config['upload']
    upload_conf = Configuration(join(path, '_oxalis', 'upload'))
    upload_conf['upload'] = upload_section
    upload_conf.save()
    os.chmod(join(path, '_oxalis', 'upload'), 0o600)
    config.remove_section('upload')
    config.remove_section('state')  # Remove also unused section 'state'
    config.save()


def _rename_text_to_md(path):
    """Change extension of Markdown files from '.text' to '.md'"""
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.text'):
                new_name = os.path.splitext(file)[0] + '.md'
                os.rename(join(root, file), join(root, new_name))


def _move_templates_to_root(path):
    """Move templates directory out from _oxalis subdir."""
    old_tpl_path = join(path, '_oxalis', 'templates')
    new_tpl_path = join(path, TEMPLATES_DIR)
    os.rename(old_tpl_path, new_tpl_path)


def _convert_templates_to_jinja(path):
    """
    Convert templates to Jinja.
    This includes changing {Tags} to {{ tags }}
    """
    tpl_tag = re.compile(r'\{(\w+)\}')
    tpl_dir = join(path, TEMPLATES_DIR)
    for filename in os.listdir(tpl_dir):
        old_path = join(tpl_dir, filename)
        with open(old_path, 'r') as file:
            old_text = file.read()
        new_text = tpl_tag.sub(lambda m: '{{ ' + m.group(1).lower() + ' }}',
                               old_text)
        new_path = old_path + '.html'
        with open(new_path, 'w') as file:
            file.write(new_text)
        os.remove(old_path)


def _change_format_version(path, version):
    """Change format version in the main configuration file."""
    config = Configuration(join(path, '_oxalis', 'config'))
    config['project']['format'] = version
    config.save()
