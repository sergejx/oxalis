import filecmp
import os
from os.path import join
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase
from oxalis.format_conversion import convert_01_to_03


class TestFormatConversion(TestCase):
    SITE_01 = join(os.path.dirname(__file__), "test-site-0.1")
    SITE_03 = join(os.path.dirname(__file__), "test-site")

    def test_conversion(self):
        with TemporaryDirectory() as tempdir:
            converted_site = join(tempdir, 'site')
            shutil.copytree(self.SITE_01, converted_site)
            convert_01_to_03(converted_site)

            # Compare files that should be same after conversion
            common = [join('_oxalis', 'config'), join('_oxalis', 'upload'),
                      'index.md', join('subdir', 'index.md')]
            match, __, __ = filecmp.cmpfiles(converted_site, self.SITE_03,
                                             common, False)
            self.assertListEqual(common, match)

            # Compare if templates are in place and contain proper tags
            default_tpl = join(converted_site, '_templates', 'default.html')
            self.assertTrue(os.path.exists(default_tpl))
            with open(default_tpl, 'r') as file:
                text = file.read()
                self.assertGreater(text.find('{{ content }}'), 0)
                self.assertGreater(text.find('{{ title }}'), 0)

            self.assertTrue(os.path.exists(
                join(converted_site, '_templates', 'second.html')))
