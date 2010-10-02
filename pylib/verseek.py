from os.path import *

import os
import re
import datetime
import subprocess

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

def getoutput(*command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()

    if p.returncode:
        raise Error("command `%s' failed" % " ".join(command))

    return p.stdout.read().rstrip("\n")

class Base:
    """version seeking base class"""
    @staticmethod
    def _parse_control(path):
        return dict([ re.split("\s*:\s+", line.strip(), 1)
                      for line in file(path).readlines()
                      if line.strip() and not line.startswith(" ") ])

    def __init__(self, path):
        if not isdir(path):
            raise Error("no such directory `%s'" % path)

        self.path = path
        self.path_changelog = join(self.path, "debian/changelog")
        self.path_control = join(self.path, "debian/control")

        if not exists(self.path_control):
            raise Error("missing debian/control file `%s'" % self.path_control)

        self.control = self._parse_control(self.path_control)
    
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
    def __init__(self, path):
        Base.__init__(self, path)
        self.gitroot = get_git_root(path)
        
    def list(self):
        return []

    def seek(self, version=None):
        pass

class GitSingle(Git):
    """version seeking class for git repository containing one package"""
    def _get_autoversion(self, commit):
        orig_cwd = os.getcwd()

        os.chdir(self.path)
        version = getoutput("autoversion", commit)
        os.chdir(orig_cwd)

        return version

    def _get_autoversion_datetime(self, version):
        orig_cwd = os.getcwd()

        os.chdir(self.path)
        commit = getoutput("autoversion", "-r", version)
        
        output = getoutput("git-cat-file", "commit", commit)
        timestamp = int(re.search(r' (\d{10}) ', output).group(1))
        dt = datetime.datetime.fromtimestamp(timestamp)
        
        os.chdir(orig_cwd)

        return dt
    
    def _create_changelog(self, version):
        release = os.environ.get("RELEASE") or "UNRELEASED"
        dt = self._get_autoversion_datetime(version)
        
        fh = file(self.path_changelog, "w")
        print >> fh, "%s (%s) %s; urgency=low" % (self.control['Source'],
                                                  version,
                                                  release)
        print >> fh
        print >> fh, "  * auto-generated changelog entry"
        print >> fh
        print >> fh, " -- %s %s" % (self.control['Maintainer'],
                                    dt.strftime("%a, %d %b %Y %H:%M:%S +0000"))
        fh.close()
        
    def seek(self, version=None):
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)
        else:
            if version != self._get_autoversion("HEAD"):
                raise Error("no such version `%s'" % version)

            self._create_changelog(version)
            
    def list(self):
        return [ self._get_autoversion("HEAD") ]

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
