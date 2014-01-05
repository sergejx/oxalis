import os

import oxalis.site

TESTDIR = os.path.join(os.path.dirname(__file__), "test-site")

def test_load():
    """Was site tree loaded properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert proj.files[""].name == "" # root
    assert proj.files["index.text"].name == "index.text"
    assert proj.files["index.text"] == proj.files["index.html"]
    assert proj.files["test.css"].name == "test.css"
    assert proj.files["subdir"].name == "subdir"
    assert proj.files["subdir/test.jpeg"].name == "test.jpeg"

def test_tree():
    """Does tree traversal works properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert len(proj.files[""].children) == 3
    assert len(proj.files["subdir"].children) == 2
    assert proj.files[""].children[0] == proj.files["subdir"]
    assert proj.files[""].children[1] == proj.files["index.text"]
    assert proj.files["subdir"].children[0] == proj.files["subdir/index.text"]
    assert proj.files["index.text"].parent == proj.files[""]
    assert proj.files["subdir/index.text"].parent == proj.files["subdir"]

def test_templates():
    """Was templates list loaded properly?"""
    proj = oxalis.site.Site(TESTDIR)
    assert len(proj.templates[""].children) == 2
    assert proj.templates["default"].name == "default"
