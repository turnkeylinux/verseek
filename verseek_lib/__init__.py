# Copyright (c) TurnKey GNU/Linux - http://www.turnkeylinux.org
#
# This file is part of Verseek
#
# Verseek is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.

from os.path import join, isdir, exists, abspath, relpath, basename

import os
import re
import datetime
import locale
import subprocess
from typing import Optional, List, Generic, Union, AnyStr, Tuple

import gitwrapper as git
from autoversion_lib import Autoversion

Locale = Tuple[Optional[str], Optional[str]]
LocaleIn = Union[Locale, Optional[str]]

class LocaleAs:

    old_locale: Locale

    def __init__(self, category: int, new_locale: LocaleIn):
        self.category = category
        self.new_locale = new_locale
        self.old_locale = None

    def __enter__(self):
        self.old_locale = locale.getlocale(self.category)
        locale.setlocale(self.category, self.new_locale)

    def __exit__(self, type, value, traceback):
        locale.setlocale(self.category, self.old_locale)


class VerseekError(Exception):
    pass


def parse_changelog(changelog: str) -> Optional[str]:
    """Parses the contents of the changelog
    
    Args:
        changelog: raw text contents of a changelog file
    
    Returns:
        the most recent version as a string or None
    """
    for line in changelog.split("\n"):
        m = re.match(r'^\w[-+0-9a-z.]* \(([^\(\) \t]+)\)(?:\s+[-+0-9a-z.]+)+\;',
                     line,
                     re.I)
        if m:
            return m.group(1)

    return None


class Base(Generic[AnyStr]):
    """Version seeking base class
    
    Attributes:
        path_changelog: a bytes or string path to the `debian/changelog` file
        path_control: a bytes or string path to the `debian/control` file
    """

    path_changelog: AnyStr
    path_control: AnyStr

    def __init__(self, path: os.PathLike):
        path = os.fspath(path)
        if not isdir(path):
            raise VerseekError(f"no such directory `{path}'")


        self.path = path
        if isinstance(path, str):
            self.path_changelog = join(self.path, "debian/changelog")
            self.path_control = join(self.path, "debian/control")
        elif isinstance(path, bytes):
            self.path_changelog = join(self.path, b"debian/changelog")
            self.path_control = join(self.path, b"debian/control")


        if not exists(self.path_control):
            raise VerseekError(
                    f"missing debian/control file `{self.path_control}'")

    def list_versions(self) -> List[str]:
        ''' Returns a list of versions for this project '''
        raise NotImplementedError()

    def seek_version(self, version=None):
        ''' Attempts to checkout a given version of this project '''
        raise NotImplementedError()


class Plain(Base):
    """Version seeking class for plain directory.

    Since plain directories don't actually support history,
    list just shows the latest version and seek is a dummy function.
    
    Attributes:
        path_changelog: a bytes or string path to the `debian/changelog` file
        path_control: a bytes or string path to the `debian/control` file
    """
    def _get_version(self) -> str:
        changelogfile = join(self.path, "debian/changelog")
        if not exists(changelogfile):
            raise VerseekError("no such file or directory `{}'"
                               "".format(changelogfile))

        with open(changelogfile, 'r') as fob:
            version = parse_changelog(fob.read())
        if not version:
            raise VerseekError("can't parse version from `{}'"
                               "".format(changelogfile))

        return version

    def list_versions(self) -> List[str]:
        ''' Returns a list of versions for this project '''
        return [self._get_version()]

    def seek_version(self, version: Optional[str]=None):
        ''' Attempts to checkout a given version of this project '''
        if version and self._get_version() != version:
            raise VerseekError("can't seek to nonexistent version `{}'"
                               "".format(version))

class Git(Base):
    """Version seeking class for git repos
    
    Uses a mixture of git tags and commit-ids to generate versions
    
    Attributes:
        path_changelog: a bytes or string path to the `debian/changelog` file
        path_control: a bytes or string path to the `debian/control` file
    """
    class Head:
        ref = "HEAD"

        def __get__(self, obj, type):
            try:
                return obj.git.symbolic_ref(self.ref)
            except git.GitError:
                raise VerseekError("HEAD isn't pointing to a branch")

    class VerseekHead:
        ref = "VERSEEK_HEAD"

        def __get__(self, obj, type):
            try:
                return obj.git.symbolic_ref(self.ref)
            except git.GitError:
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
    def get_git_root(directory: os.PathLike) -> Optional[os.PathLike]:
        """Walk up dir until we get the gitdir.

        Args:
            directory: pathlike pointing towards a git repo

        Returns:
            a path to the `.git` directory of a git repo or `None` if no
            `.git` directory is found
        """
        directory = os.fspath(directory)
        directory = abspath(directory)

        root = '/' if isinstance(directory, str) else b'/'
        git_dir = '.git' if isinstance(directory, str) else b'.git'

        while True:
            if isdir(join(directory, git_dir)):
                return directory

            directory, _ = os.path.split(directory)
            if directory == root:
                return None

    def __init__(self, path: os.PathLike):
        Base.__init__(self, path)
        self.git = git.Git(self.get_git_root(self.path))

    def _list_versions(self) -> List[Tuple[str, str]]:
        branch = basename(self.verseek_head or self.head)

        path_changelog = relpath(self.path_changelog, self.git.path)
        commits = self.git.rev_list(branch, path_changelog)

        changelogs = [self.git.cat_file("blob",
                                        commit + ":" + path_changelog)
                      for commit in commits]

        versions = [parse_changelog(changelog) for changelog in changelogs]
        #return list(filter(lambda x:x[0], zip(versions, commits)))
        return [
            (version, commit) for (version, commit) in zip(versions, commits)
                if version
        ]

    def list_versions(self) -> List[str]:
        ''' Returns a list of versions for this project '''
        return [version for version, commit in self._list_versions()]

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

    def seek_version(self, version: Optional[str]=None):
        ''' Attempts to checkout a given version of this project '''
        if not version:
            self._seek_restore()
        else:
            versions = dict(self._list_versions())
            if version not in versions:
                raise VerseekError("no such version `{}'".format(version))

            commit = versions[version]
            self._seek_commit(commit)


class GitSingle(Git):
    """version seeking class for git repository containing one package"""
    def __init__(self, path: os.PathLike):
        Git.__init__(self, path)
        self.autoversion = Autoversion(path, precache=True)

    def _get_commit_datetime(self, commit: str) -> datetime.datetime:
        output = self.git.cat_file("commit", commit)
        timestamp = int(re.search(r' (\d{10}) ', output).group(1))
        return datetime.datetime.utcfromtimestamp(timestamp)

    def _create_changelog(self, version, entry_datetime: datetime.datetime):
        release = "UNRELEASED"

        def parse_control(path):
            with open(path, 'r') as fob:
                lines = (line.rstrip() for line in fob
                    if not line.startswith(' '))
            return dict([re.split(r"\s*:\s*", line, 1)
                         for line in lines
                         if line and ':' in line])

        control = parse_control(self.path_control)

        with LocaleAs(locale.LC_TIME, 'C'):
            with open(self.path_changelog, 'w') as fob:
                print("{} ({}) {}; urgency=low"
                      "".format(control['Source'],
                                version,
                                release),
                      file=fob)
                print(file=fob)
                print("  * undocumented", file=fob)
                print(file=fob)
                print(" --  {}  {}"
                      "".format(control['Maintainer'],
                                entry_datetime.strftime("%a, %d %b %Y %H:%M:%S +0000")),
                      file=fob)

    def seek_version(self, version: Optional[str]=None):
        ''' Attempts to checkout a given version of this project '''
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)

            self._seek_restore()
        else:
            commit = self.autoversion.version2commit(version)
            self._seek_commit(commit)
            self._create_changelog(version, self._get_commit_datetime(commit))

    def list_versions(self) -> List[str]:
        ''' Returns a list of versions for this project '''
        branch = basename(self.verseek_head or self.head)

        commits = self.git.rev_list(branch)
        return [self.autoversion.commit2version(commit)
                for commit in commits]

def new(path: os.PathLike) -> Base:
    """Return instance appropriate for path
    
    Args:
        path: path to project as any os.PathLike (including str, bytes,
              pathlib.Path, etc.)

    Returns:
        An object that inherits from `verseek_lib.Base`
            - `verseek_lib.GitSingle` if `.git` and `debian/control` are found
            - `verseek_lib.Git` if `.git` is found
            - `verseek_lib.Plain` otherwise
    """

    root = Git.get_git_root(path)
    if root:
        if exists(join(root, "debian/control")):
            return GitSingle(path)

        return Git(path)
    return Plain(path)


def list_versions(path: os.PathLike) -> List[str]:
    """List versions of project found at path
    
    Args:
        path: path to project as any os.PathLike (including str, bytes,
              pathlib.Path, etc.)

    Returns:
        a list of versions as strings
    """
    return new(path).list_versions()


def seek_version(path: os.PathLike, version: Optional[str]=None):
    """Seek to <version> in Debian source package at <path>.
    If <version> is None, unseek.

    Note: how this is implemented depends on the path type.

    Args:
        path: path to project as any os.PathLike (including str, bytes,
              pathlib.Path, etc.)
    """
    return new(path).seek_version(version)
