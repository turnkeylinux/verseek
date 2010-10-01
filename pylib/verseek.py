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


    
def get_git_root(dir):
    """Walk up dir to get the gitdir.
    Return None if we're not in a repository"""
    dir = abspath(dir)
    
    subdir = None
    while True:
        if isdir(join(dir, ".git")):
            return dir


        dir, subdir = split(dir)
        if dir == '/':
            return None

class Base:
    """version seeking base class"""
    def __init__(self, path):
        if not isdir(path):
            raise Error("no such directory `%s'" % path)
        self.path = path
    
    def list(self):
        return []

    def seek(self, version=None):
        pass

class Plain(Base):
    """version seeking class for plain directory"""
    def list(self):
        return [ deb_get_version(self.path) ]

    def seek(self, version=None):
        if version and deb_get_version(path) != version:
            raise Error("can't seek to nonexistent version `%s'" % version)


class Git(Base):
    """version seeking class for git"""
    def list(self):
        return []

    def seek(self, version=None):
        pass

class GitSingle(Base):
    """version seeking class for git repository containing one package"""
    def list(self):
        return []

    def seek(self, version=None):
        pass

class Sumo(Base):
    """version seeking class for Sumo storage type"""
    def list(self):
        return []

    def seek(self, version=None):
        pass

def new(path):
    """Return  instance appropriate for path"""

    root = get_git_root(path)
    if root:
        if exists(join(root, "debian/control")):
            return GitSingle(path)

        if isdir(join(root, "arena.internals")):
            return Sumo(path)
        
        return Git(path)

    return Plain(path)
    
def list(path):
    """List versions at path"""
    return new(path).list()

def seek(path, version=None):
    """ """
    return new(path).seek(version)
