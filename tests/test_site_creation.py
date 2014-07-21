import os
import stat
import shutil

import oxalis.site

TESTDIR = os.path.join(os.path.dirname(__file__), "working")
CONFDIR = os.path.join(TESTDIR, "_oxalis")

def perm(path):
    """Get file permissioms"""
    return stat.S_IMODE(os.stat(path).st_mode)

def setup():
    os.mkdir(TESTDIR)
    oxalis.site.create_site(TESTDIR)

def teardown():
    shutil.rmtree(TESTDIR)

def test_site_dir():
    """Was site dir created?"""
    assert os.path.isdir(TESTDIR)

def test_config():
    """Was site configuration created with right permissions?"""
    assert os.path.isdir(CONFDIR)
    conffile = os.path.join(CONFDIR, "config")
    assert os.path.exists(conffile)
    assert perm(conffile) == 0o600

def test_sitecopy_config():
    """Was Sitecopy configuration created with right permissions?"""
    scdir = os.path.join(CONFDIR, "sitecopy")
    assert os.path.isdir(scdir)
    assert perm(scdir) == 0o700
    scconf = os.path.join(CONFDIR, "sitecopyrc")
    assert os.path.exists(scconf)
    assert perm(scconf) == 0o600

def test_index_templates():
    """Was index file and templates created?"""
    assert os.path.exists(os.path.join(TESTDIR, "index.text"))
    tpldir = os.path.join(CONFDIR, "templates")
    assert os.path.isdir(tpldir)
    assert os.path.exists(os.path.join(tpldir, "default"))
