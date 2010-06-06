import os

import oxalis.project

TESTDIR = os.path.join(os.path.dirname(__file__), "test-project")

def test_load():
    """Was project tree loaded properly?"""
    proj = oxalis.project.Project(TESTDIR)
    assert proj.files[""].name == "" # root
    assert proj.files["index.html"].name == "index.html"
    assert proj.files["test.css"].name == "test.css"
    assert proj.files["subdir"].name == "subdir"
    assert proj.files["subdir/test.jpeg"].name == "test.jpeg"

def test_tree():
    """Does tree traversal works properly?"""
    proj = oxalis.project.Project(TESTDIR)
    assert len(proj.files[""].children) == 3
    assert len(proj.files["subdir"].children) == 2
    assert proj.files[""].children[0] == proj.files["subdir"]
    assert proj.files[""].children[1] == proj.files["index.html"]
    assert proj.files["subdir"].children[0] == proj.files["subdir/index.html"]
    assert proj.files["index.html"].parent == proj.files[""]
    assert proj.files["subdir/index.html"].parent == proj.files["subdir"]

def test_templates():
    """Was templates list loaded properly?"""
    proj = oxalis.project.Project(TESTDIR)
    assert len(proj.templates[""].children) == 2
    assert proj.templates["default"].name == "default"
