from os.path import *

import os
import re
import datetime
import commands

from subprocess import *

class Error(Exception):
    pass

def getoutput(*command):
    """executes command and returns stdout output on success, None on error."""
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    output = p.communicate()[0]

    if p.returncode:
        return None

    return output.rstrip("\n")

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

class Base(object):
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
        if version and deb_get_version(self.path) != version:
            raise Error("can't seek to nonexistent version `%s'" % version)

class Git(Plain):
    """version seeking class for git"""

class GitSingle(Git):
    """version seeking class for git repository containing one package"""
    class Head(object):
        ref = "HEAD"
        def __get__(self, obj, type):
            try:
                return obj._getoutput("git-symbolic-ref", self.ref)
            except Error:
                raise Error("HEAD isn't pointing to a branch")

    class VerseekHead(object):
        ref = "VERSEEK_HEAD"
        def __get__(self, obj, type):
            try:
                return obj._getoutput("git-symbolic-ref", self.ref)
            except Error:
                return None

        def __set__(self, obj, val):
            if val is None:
                ref_path = join(obj.path, ".git", self.ref)
                if exists(ref_path):
                    os.remove(ref_path)
            else:
                obj._getoutput("git-symbolic-ref", self.ref, val)

    verseek_head = VerseekHead()
    head = Head()
    
    def _system(self, command, *args):
        orig_cwd = os.getcwd()
        os.chdir(self.path)
        command = command + " " + " ".join([commands.mkarg(arg) for arg in args])
        err = os.system(command)
        os.chdir(orig_cwd)
        if err:
            raise Error("command failed: " + command,
                        os.WEXITSTATUS(err))

    def _getoutput(self, *command):
        orig_cwd = os.getcwd()
        os.chdir(self.path)
        output = getoutput(*command)
        os.chdir(orig_cwd)

        if output is None:
            raise Error("command failed: `%s'" % " ".join(command))
            
        return output

    def _get_commit_datetime(self, commit):
        output = self._getoutput("git-cat-file", "commit", commit)
        timestamp = int(re.search(r' (\d{10}) ', output).group(1))
        return datetime.datetime.fromtimestamp(timestamp)

    def _create_changelog(self, version, datetime):
        release = os.environ.get("RELEASE") or "UNRELEASED"
        
        fh = file(self.path_changelog, "w")
        print >> fh, "%s (%s) %s; urgency=low" % (self.control['Source'],
                                                  version,
                                                  release)
        print >> fh
        print >> fh, "  * auto-generated changelog entry"
        print >> fh
        print >> fh, " --  %s  %s" % (self.control['Maintainer'],
                                      datetime.strftime("%a, %d %b %Y %H:%M:%S +0000"))
        fh.close()

    def seek(self, version=None):
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)

            if not self.verseek_head:
                raise Error("no version to seek back to")
            
            self._system("git-checkout -q -f", basename(self.verseek_head))
            self.verseek_head = None
        else:
            try:
                commit = self._getoutput("autoversion", "-r", version)
            except Error:
                raise Error("no such version `%s'" % version)

            if not self.verseek_head:
                self.verseek_head = self.head

            self._system("git-checkout -q -f", commit)
            self._create_changelog(version, self._get_commit_datetime(commit))
            
    def list(self):
        commits = self._getoutput("git-rev-list", "--all").split("\n")
        return self._getoutput("autoversion", *commits).split("\n")

class Sumo(Plain):
    """version seeking class for Sumo storage type"""

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
