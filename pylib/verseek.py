from os.path import *

import os
import re
import datetime
import commands

from subprocess import *
from executil import system

class Error(Exception):
    pass

def getoutput(*command):
    """executes command and returns stdout output on success, None on error."""
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    output = p.communicate()[0]

    if p.returncode:
        return None

    return output.rstrip("\n")

def parse_changelog(changelog):
    """Parses the contents of the changelog -> returns latest version"""
    for line in changelog.split("\n"):
        m = re.match('^\w[-+0-9a-z.]* \(([^\(\) \t]+)\)(?:\s+[-+0-9a-z.]+)+\;',line
, re.I)
        if m:
            return m.group(1)

    return None
    
class Base(object):
    """version seeking base class"""
    def __init__(self, path):
        if not isdir(path):
            raise Error("no such directory `%s'" % path)

        self.path = path
        self.path_changelog = join(self.path, "debian/changelog")
        self.path_control = join(self.path, "debian/control")

        if not exists(self.path_control):
            raise Error("missing debian/control file `%s'" % self.path_control)

    def list(self):
        return []

    def seek(self, version=None):
        pass

class Plain(Base):
    """Version seeking class for plain directory.

    Since plain directories don't actually support history,
    list just shows the latest version and seek is a dummy function.
    """
    def _get_version(self):
        changelogfile = join(self.path, "debian/changelog")
        if not exists(changelogfile):
            raise Error("no such file or directory `%s'" % changelogfile)

        version = parse_changelog(file(changelogfile).read())
        if not version:
            raise Error("can't parse version from `%s'" % changelogfile)

        return version

    def list(self):
        return [ self._get_version() ]

    def seek(self, version=None):
        if version and self._get_version() != version:
            raise Error("can't seek to nonexistent version `%s'" % version)

def make_relative(root, path):
    """Return <path> relative to <root>.

    For example:
        make_relative("../../", "file") == "path/to/file"
        make_relative("/root", "/tmp") == "../tmp"
        make_relative("/root", "/root/backups/file") == "backups/file"
        
    """

    up_count = 0

    root = realpath(root).rstrip('/')
    path = realpath(path).rstrip('/')

    while True:
        if path == root or path.startswith(root.rstrip("/") + "/"):
            return ("../" * up_count) + path[len(root) + 1:]

        root = dirname(root).rstrip('/')
        up_count += 1

class Git(Base):
    """version seeking class for git"""
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
        os.chdir(self.git_root)
        try:
            system(command, *args)
        finally:
            os.chdir(orig_cwd)

    def _getoutput(self, *command):
        orig_cwd = os.getcwd()
        os.chdir(self.git_root)
        output = getoutput(*command)
        os.chdir(orig_cwd)

        if output is None:
            raise Error("command failed: `%s'" % " ".join(command))
            
        return output

    @staticmethod
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

    def __init__(self, path):
        Base.__init__(self, path)
        self.git_root = self.get_git_root(self.path)

    def _list(self):
        branch = basename(self.verseek_head or self.head)

        path_changelog = make_relative(self.git_root, self.path_changelog)
        commits = self._getoutput("git-rev-list", branch,
                                  path_changelog).split("\n")

        changelogs = [ self._getoutput("git-cat-file", "blob",
                                       commit + ":" + path_changelog)
                       for commit in commits ]
        
        versions = [ parse_changelog(changelog) for changelog in changelogs ]
        return zip(versions, commits)

    def list(self):
        return [ version for version, commit in self._list() ]

    CMD_CHECKOUT = "git-checkout -q -f"

    def _seek_restore(self):
        """restore repository to state before seek"""
        if not self.verseek_head:
            raise Error("no version to seek back to")

        self._system(self.CMD_CHECKOUT, basename(self.verseek_head))
        self.verseek_head = None

    def _seek_commit(self, commit):
        if not self.verseek_head:
            self.verseek_head = self.head

        self._system(self.CMD_CHECKOUT, commit)

    def seek(self, version=None):
        if not version:
            self._seek_restore()
        else:
            versions = dict(self._list())
            if version not in versions:
                raise Error("no such version `%s'" % version)

            commit = versions[version]
            self._seek_commit(commit)

class GitSingle(Git):
    """version seeking class for git repository containing one package"""
    def _get_commit_datetime(self, commit):
        output = self._getoutput("git-cat-file", "commit", commit)
        timestamp = int(re.search(r' (\d{10}) ', output).group(1))
        return datetime.datetime.fromtimestamp(timestamp)

    def _create_changelog(self, version, datetime):
        release = os.environ.get("RELEASE") or "UNRELEASED"
        
        def parse_control(path):
            lines = (line.rstrip() for line in file(path).readlines()
                     if not line.startswith(" "))
            return dict([ re.split("\s*:\s*", line, 1)
                          for line in lines
                          if line ])

        control = parse_control(self.path_control)

        fh = file(self.path_changelog, "w")
        print >> fh, "%s (%s) %s; urgency=low" % (control['Source'],
                                                  version,
                                                  release)
        print >> fh
        print >> fh, "  * auto-generated changelog entry"
        print >> fh
        print >> fh, " --  %s  %s" % (control['Maintainer'],
                                      datetime.strftime("%a, %d %b %Y %H:%M:%S +0000"))
        fh.close()

    def seek(self, version=None):
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)

            self._seek_restore()
        else:
            try:
                commit = self._getoutput("autoversion", "-r", version)
            except Error:
                raise Error("no such version `%s'" % version)

            self._seek_commit(commit)
            self._create_changelog(version, self._get_commit_datetime(commit))
            
    def list(self):
        branch = basename(self.verseek_head or self.head)
        
        commits = self._getoutput("git-rev-list", branch).split("\n")
        return self._getoutput("autoversion", *commits).split("\n")

class Sumo(Git):
    """version seeking class for Sumo storage type"""

    def _list(self):
        branch = basename(self.verseek_head or self.head) + "-thin"

        path_relative = make_relative(join(self.git_root, "arena.union"),
                                      self.path_changelog)

        path_internals = join(self.git_root, "arena.internals/overlay", path_relative)
        path_changelog = make_relative(self.git_root, path_internals)
        
        commits = self._getoutput("git-rev-list", branch,
                                  path_changelog).split("\n")
        

        changelogs = [ self._getoutput("git-cat-file", "blob",
                                       commit + ":" + path_changelog)
                       for commit in commits ]
        
        versions = [ parse_changelog(changelog) for changelog in changelogs ]
        return zip(versions, commits)

    CMD_CHECKOUT = "sumo-checkout"

def new(path):
    """Return  instance appropriate for path"""

    root = Git.get_git_root(path)
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
