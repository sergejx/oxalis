import os

import oxalis.site

TESTDIR = os.path.join(os.path.dirname(__file__), "test-site")


def test_load():
    """Was site tree loaded properly?"""
    site = oxalis.site.Site(TESTDIR)
    pass


def test_tree():
    """Does tree traversal works properly?"""
    site = oxalis.site.Site(TESTDIR)
    pass