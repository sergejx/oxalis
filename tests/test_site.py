import os
from unittest import TestCase

import oxalis.site

TESTDIR = os.path.join(os.path.dirname(__file__), "test-site")


class TestSite(TestCase):
    def test_load(self):
        """Was site tree loaded properly?"""
        site = oxalis.site.Site(TESTDIR)
        self.assertEqual(site.store.get_by_path("").name, "")  # root
        self.assertEqual(site.store.get_by_path("index.md").name, "index.md")
        with self.assertRaises(KeyError):
            site.store.get_by_path("index.html")
        self.assertEqual(site.store.get_by_path("test.css").name, "test.css")
        self.assertEqual(site.store.get_by_path("subdir").name, "subdir")
        self.assertEqual(site.store.get_by_path("subdir/test.jpeg").name,
                         "test.jpeg")

    def test_tree(self):
        """Does tree traversal works properly?"""
        site = oxalis.site.Site(TESTDIR)
        root = site.store.get_by_path("")
        subdir = site.store.get_by_path("subdir")
        index = site.store.get_by_path("index.md")
        subdir_index = site.store.get_by_path("subdir/index.md")
        self.assertEqual(len(site.store.get_children(root)), 4)
        self.assertEqual(len(site.store.get_children(subdir)), 2)
        self.assertIn(subdir, site.store.get_children(root))
        self.assertIn(index, site.store.get_children(root))
        self.assertIn(subdir_index, site.store.get_children(subdir))
        self.assertEqual(site.store.get_parent(index), root)
        self.assertEqual(site.store.get_parent(subdir_index), subdir)
