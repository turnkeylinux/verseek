import re
from os.path import *

class Error(Exception):
    pass

def deb_get_version(srcpath):
    changelogfile = join(srcpath, "debian/changelog")
    if not exists(changelogfile):
        raise Error("no such file or directory `%s'" % changelogfile)

    for line in file(changelogfile).readlines():
        m = re.match('^\w[-+0-9a-z.]* \(([^\(\) \t]+)\)(?:\s+[-+0-9a-z.]+)+\;',line
, re.I)
        if m:
            return m.group(1)

    raise Error("can't parse version from `%s'" % changelogfile)

def list(path):
    return [ deb_get_version(path) ]

def seek(path, version=None):
    if version and deb_get_version(path) != version:
        raise Error("can't seek to nonexistent version `%s'" % version)

