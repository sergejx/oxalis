import os

import oxalis.site

TESTDIR = os.path.join(os.path.dirname(__file__), "test-site")

def test_load():
    """Was site tree loaded properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert proj.get_document("").name == "" # root
    assert proj.get_document("index.text").name == "index.text"
    assert proj.get_document("index.text") == proj.get_document("index.html")
    assert proj.get_document("test.css").name == "test.css"
    assert proj.get_document("subdir").name == "subdir"
    assert proj.get_document("subdir/test.jpeg").name == "test.jpeg"

def test_tree():
    """Does tree traversal works properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert len(proj.get_document("").children) == 3
    assert len(proj.get_document("subdir").children) == 2
    assert proj.get_document("").children[0] == proj.get_document("subdir")
    assert proj.get_document("").children[1] == proj.get_document("index.text")
    assert proj.get_document("subdir").children[0] == proj.get_document("subdir/index.text")
    assert proj.get_document("index.text").parent == proj.get_document("")
    assert proj.get_document("subdir/index.text").parent == proj.get_document("subdir")

def test_templates():
    """Was templates list loaded properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert len(proj.get_document("", True).children) == 2
    assert proj.get_document("default", True).name == "default"
