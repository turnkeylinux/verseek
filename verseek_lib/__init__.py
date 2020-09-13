# Copyright (c) TurnKey GNU/Linux - http://www.turnkeylinux.org
#
# This file is part of Verseek
#
# Verseek is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.

from os.path import *  #

import os
import re
import datetime
import locale
import subprocess

import gitwrapper as git
from autoversion import Autoversion
#from pyproject.autoversion.autoversion import Autoversion


class LocaleAs(object):
    def __init__(self, category, new_locale):
        self.category = category
        self.new_locale = new_locale

    def __enter__(self):
        self.old_locale = locale.getlocale(self.category)
        locale.setlocale(self.category, self.new_locale)

    def __exit__(self, type, value, traceback):
        locale.setlocale(self.category, self.old_locale)


class VerseekError(Exception):
    pass


def parse_changelog(changelog):
    """Parses the contents of the changelog -> returns latest version"""
    for line in changelog.split("\n"):
        m = re.match('^\w[-+0-9a-z.]* \(([^\(\) \t]+)\)(?:\s+[-+0-9a-z.]+)+\;',
                     line,
                     re.I)
        if m:
            return m.group(1)

    return None


class Base(object):
    """version seeking base class"""
    def __init__(self, path):
        if not isdir(path):
            raise VerseekError("no such directory `%s'" % path)

        self.path = path
        self.path_changelog = join(self.path, "debian/changelog")
        self.path_control = join(self.path, "debian/control")

        if not exists(self.path_control):
            raise VerseekError("missing debian/control file `{}'"
                               "".format(self.path_control))

    def list_(self):
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
            raise VerseekError("no such file or directory `{}'"
                               "".format(changelogfile))

        version = parse_changelog(file(changelogfile).read())
        if not version:
            raise VerseekError("can't parse version from `{}'"
                               "".format(changelogfile))

        return version

    def list_(self):
        return [self._get_version()]

    def seek(self, version=None):
        if version and self._get_version() != version:
            raise VerseekError("can't seek to nonexistent version `{}'"
                               "".format(version))


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
                return obj.git.symbolic_ref(self.ref)
            except obj.git.Error:
                raise VerseekError("HEAD isn't pointing to a branch")

    class VerseekHead(object):
        ref = "VERSEEK_HEAD"

        def __get__(self, obj, type):
            try:
                return obj.git.symbolic_ref(self.ref)
            except obj.git.Error:
                return None

        def __set__(self, obj, val):
            if val is None:
                ref_path = join(obj.path, ".git", self.ref)
                if exists(ref_path):
                    os.remove(ref_path)
            else:
                obj.git.symbolic_ref(self.ref, val)

    verseek_head = VerseekHead()
    head = Head()

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
        self.git = git.Git(self.get_git_root(self.path))

    def _list(self):
        branch = basename(self.verseek_head or self.head)

        path_changelog = make_relative(self.git.path, self.path_changelog)
        commits = self.git.rev_list(branch, path_changelog)

        changelogs = [self.git.cat_file("blob",
                                        commit + ":" + path_changelog)
                      for commit in commits]

        versions = [parse_changelog(changelog) for changelog in changelogs]
        return list_(zip(versions, commits))

    def list_(self):
        return [version for version, commit in self._list()]

    def _checkout(self, arg):
        self.git.checkout("-q", "-f", arg)

    def _seek_restore(self):
        """restore repository to state before seek"""
        if not self.verseek_head:
            raise VerseekError("no version to seek back to")

        self._checkout(basename(self.verseek_head))
        self.verseek_head = None

    def _seek_commit(self, commit):
        if not self.verseek_head:
            self.verseek_head = self.head

        self._checkout(commit)

    def seek(self, version=None):
        if not version:
            self._seek_restore()
        else:
            versions = dict(self._list())
            if version not in versions:
                raise VerseekError("no such version `{}'".format(version))

            commit = versions[version]
            self._seek_commit(commit)


class GitSingle(Git):
    """version seeking class for git repository containing one package"""
    def __init__(self, path):
        Git.__init__(self, path)
        self.autoversion = Autoversion(path, precache=True)

    def _get_commit_datetime(self, commit):
        output = self.git.cat_file("commit", commit)
        timestamp = int(re.search(r' (\d{10}) ', output).group(1))
        return datetime.datetime.utcfromtimestamp(timestamp)

    def _create_changelog(self, version, datetime):
        release = "UNRELEASED"

        def parse_control(path):
            lines = (line.rstrip() for line in file(path).readlines()
                     if not line.startswith(" "))
            return dict([re.split("\s*:\s*", line, 1)
                         for line in lines
                         if line and ':' in line])

        control = parse_control(self.path_control)

        with LocaleAs(locale.LC_TIME, 'C'):
            fh = file(self.path_changelog, "w")
            print("{} ({}) {}; urgency=low"
                  "".format(control['Source'],
                            version,
                            release),
                  file=fh)
            print(file=fh)
            print("  * undocumented", file=fh)
            print(file=fh)
            print(" --  {}  {}"
                  "".format(control['Maintainer'],
                            datetime.strftime("%a, %d %b %Y %H:%M:%S +0000")),
                  file=fh)
            fh.close()

    def seek(self, version=None):
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)

            self._seek_restore()
        else:
            commit = self.autoversion.version2commit(version)
            self._seek_commit(commit)
            self._create_changelog(version, self._get_commit_datetime(commit))

    def list_(self):
        branch = basename(self.verseek_head or self.head)

        commits = self.git.rev_list(branch)
        return [self.autoversion.commit2version(commit)
                for commit in commits]


class Sumo(Git):
    """version seeking class for Sumo storage type"""

    def _list(self):
        branch = basename(self.verseek_head or self.head) + "-thin"

        path_relative = make_relative(join(self.git.path, "arena.union"),
                                      self.path_changelog)

        path_internals = join(self.git.path, "arena.internals/overlay",
                              path_relative)
        path_changelog = make_relative(self.git.path, path_internals)

        commits = self.git.rev_list(branch, path_changelog)
        changelogs = [self.git.cat_file("blob",
                                        commit + ":" + path_changelog)
                      for commit in commits]

        versions = [parse_changelog(changelog) for changelog in changelogs]
        return list_(zip(versions, commits))

    def _checkout(self, arg):
        orig_cwd = os.getcwd()
        os.chdir(self.git.path)
        subprocess.run(["sumo-checkout", arg])
        os.chdir(orig_cwd)


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


def list_(path):
    """List versions at path"""
    return new(path)._list()


def seek(path, version=None):
    """Seek to <version> in Debian source package at <path>.
    If <version> is None, unseek.

    Note: how this is implemented depends on the path type."""
    return new(path).seek(version)
