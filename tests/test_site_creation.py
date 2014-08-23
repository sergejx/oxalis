import os
import stat
import shutil
from unittest import TestCase

import oxalis.site

TEST_DIR = os.path.join(os.path.dirname(__file__), "working")
CONF_DIR = os.path.join(TEST_DIR, "_oxalis")


def perm(path):
    """Get file permissions"""
    return stat.S_IMODE(os.stat(path).st_mode)


class TestSiteCreation(TestCase):
    def setUp(self):
        os.mkdir(TEST_DIR)
        oxalis.site.create_site(TEST_DIR)

    def tearDown(self):
        shutil.rmtree(TEST_DIR)

    def test_site_dir(self):
        """Was site dir created?"""
        self.assertTrue(os.path.isdir(TEST_DIR))

    def test_site_format(self):
        self.assertEqual(oxalis.site.check_site_format(TEST_DIR), '0.3')

    def test_config(self):
        """Was site configuration created with right permissions?"""
        self.assertTrue(os.path.isdir(CONF_DIR))
        conf_file = os.path.join(CONF_DIR, "config")
        self.assertTrue(os.path.exists(conf_file))
        upload_conf = os.path.join(CONF_DIR, "upload")
        self.assertTrue(os.path.exists(upload_conf))
        self.assertEqual(perm(upload_conf), 0o600)

    def test_sitecopy_config(self):
        """Was Sitecopy configuration created with right permissions?"""
        sc_dir = os.path.join(CONF_DIR, "sitecopy")
        self.assertTrue(os.path.isdir(sc_dir))
        self.assertEqual(perm(sc_dir), 0o700)
        sc_conf = os.path.join(CONF_DIR, "sitecopyrc")
        self.assertTrue(os.path.exists(sc_conf))
        self.assertEqual(perm(sc_conf), 0o600)

    def test_index_templates(self):
        """Was index file and templates created?"""
        self.assertTrue(os.path.exists(os.path.join(TEST_DIR, "index.md")))
        tpl_dir = os.path.join(TEST_DIR, "_templates")
        self.assertTrue(os.path.isdir(tpl_dir))
        self.assertTrue(os.path.exists(os.path.join(tpl_dir, "default.html")))
