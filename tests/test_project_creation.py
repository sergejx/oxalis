import os
import stat
import shutil

import oxalis.project

testdir = os.path.join(os.path.dirname(__file__), "working")
confdir = os.path.join(testdir, "_oxalis")

def perm(path):
    """Get file permissioms"""
    return stat.S_IMODE(os.stat(path).st_mode)

def setup():
    global testdir
    os.mkdir(testdir)
    oxalis.project.create_project(testdir)

def teardown():
    global testdir
    shutil.rmtree(testdir)

def test_project_dir():
    """Was project dir created?"""
    global testdir
    assert os.path.isdir(testdir)

def test_config():
    """Was project configuration created with right permissions?"""
    global confdir
    assert os.path.isdir(confdir)
    conffile = os.path.join(confdir, "config")
    assert os.path.exists(conffile)
    assert perm(conffile) == 0600

def test_sitecopy_config():
    """Was Sitecopy configuration created with right permissions?"""
    global confdir
    scdir = os.path.join(confdir, "sitecopy")
    assert os.path.isdir(scdir)
    assert perm(scdir) == 0700
    scconf = os.path.join(confdir, "sitecopyrc")
    assert os.path.exists(scconf)
    assert perm(scconf) == 0600

def test_index_templates():
    """Was index file and templates created?"""
    global testdir, confdir
    assert os.path.exists(os.path.join(testdir, "index.text"))
    tpldir = os.path.join(confdir, "templates")
    assert os.path.isdir(tpldir)
    assert os.path.exists(os.path.join(tpldir, "default"))
