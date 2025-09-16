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
from typing import Generic, TypeVar
from types import TracebackType
from collections.abc import Iterable

import gitwrapper as git
from autoversion_lib import Autoversion

Locale = str | Iterable[str] | None
# should probably be: ?
#Locale = tuple[str | None, str | None] | None
AnyPath = TypeVar("AnyPath", str, os.PathLike)


def fspath(p: AnyPath) -> str:
    return os.fspath(p)


class LocaleAs:
    old_locale: Locale

    def __init__(self, category: int, new_locale: Locale) -> None:
        self.category = category
        self.new_locale = new_locale
        self.old_locale = None

    def __enter__(self) -> None:
        # expression has type "Tuple[Optional[str], Optional[str]]",
        # variable has type "Union[str, Iterable[str], None]
        # see commented 'Locale =' line above
        self.old_locale = locale.getlocale(self.category)
        locale.setlocale(self.category, self.new_locale)

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        locale.setlocale(self.category, self.old_locale)


class VerseekError(Exception):
    pass


def parse_changelog(changelog: str) -> str | None:
    """Parses the contents of the changelog

    Args:
        changelog: raw text contents of a changelog file

    Returns:
        the most recent version as a string or None
    """
    for line in changelog.split("\n"):
        m = re.match(
            r"^\w[-+0-9a-z.]* \(([^\(\) \t]+)\)(?:\s+[-+0-9a-z.]+)+\;",
            line,
            re.I,
        )
        if m:
            return m.group(1)

    return None


class Base(Generic[AnyPath]):
    """Version seeking base class

    Attributes:
        path_changelog: a path to the `debian/changelog` file
        path_control: a path to the `debian/control` file
    """

    path_changelog: str
    path_control: str

    def __init__(self, path: AnyPath) -> None:
        spath = fspath(path)
        if not isdir(spath):
            raise VerseekError(f"no such directory `{path}'")

        self.path = spath
        self.path_changelog = join(self.path, "debian/changelog")
        self.path_control = join(self.path, "debian/control")

        if not exists(self.path_control):
            raise VerseekError(
                f"missing debian/control file `{self.path_control}'"
            )

    def list_versions(self) -> list[str]:
        """Returns a list of versions for this project"""
        raise NotImplementedError()

    def seek_version(self, version: str | None = None) -> None:
        """Attempts to checkout a given version of this project"""
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
            raise VerseekError("no such file or directory `{changelogfile}'")

        with open(changelogfile) as fob:
            version = parse_changelog(fob.read())
        if not version:
            raise VerseekError("can't parse version from `{changelogfile}'")

        return version

    def list_versions(self) -> list[str]:
        """Returns a list of versions for this project"""
        return [self._get_version()]

    def seek_version(self, version: str | None = None) -> None:
        """Attempts to checkout a given version of this project"""
        if version and self._get_version() != version:
            raise VerseekError(f"can't seek to nonexistent version `{version}'")


class Git(Base):
    """Version seeking class for git repos

    Uses a mixture of git tags and commit-ids to generate versions

    Attributes:
        path_changelog: a bytes or string path to the `debian/changelog` file
        path_control: a bytes or string path to the `debian/control` file
    """

    class Head:
        ref = "HEAD"

        def __get__(self, obj: "Git", type: type["Git"]) -> str:
            try:
                return obj.git.symbolic_ref(self.ref)
            except git.GitError as e:
                raise VerseekError("HEAD isn't pointing to a branch") from e

    class VerseekHead:
        ref = "VERSEEK_HEAD"

        def __get__(self, obj: "Git", type: type["Git"]) -> str | None:
            try:
                return obj.git.symbolic_ref(self.ref)
            except git.GitError:
                return None

        def __set__(self, obj: "Git", val: str | None) -> None:
            if val is None:
                ref_path = join(obj.path, ".git", self.ref)
                if exists(ref_path):
                    os.remove(ref_path)
            else:
                obj.git.symbolic_ref(self.ref, val)

    verseek_head = VerseekHead()
    head = Head()

    @staticmethod
    def get_git_root(directory: AnyPath) -> AnyPath | None:
        """Walk up dir until we get the gitdir.

        Args:
            directory: pathlike pointing towards a git repo

        Returns:
            a path to the `.git` directory of a git repo or `None` if no
            `.git` directory is found
        """
        sdirectory = fspath(directory)
        sdirectory = abspath(sdirectory)

        root = "/"
        git_dir = ".git"

        while True:
            if isdir(join(directory, git_dir)):
                return directory

            directory, _ = os.path.split(directory)
            if directory == root:
                return None

    def __init__(self, path: AnyPath) -> None:
        Base.__init__(self, path)
        git_root = self.get_git_root(self.path)
        assert git_root is not None
        self.git = git.Git(git_root)

    def _list_versions(self) -> list[tuple[str, str]]:
        branch = basename(self.verseek_head or self.head)

        path_changelog = relpath(self.path_changelog, self.git.path)
        commits = self.git.rev_list(branch, path_changelog)

        changelogs = [
            self.git.cat_file("blob", commit + ":" + path_changelog)
            for commit in commits
        ]

        versions = [parse_changelog(changelog) for changelog in changelogs]
        return [
            (version, commit)
            for (version, commit) in zip(versions, commits)
            if version
        ]

    def list_versions(self) -> list[str]:
        """Returns a list of versions for this project"""
        return [version for version, commit in self._list_versions()]

    def _checkout(self, arg: str) -> None:
        self.git.checkout("-q", "-f", arg)

    def _seek_restore(self) -> None:
        """restore repository to state before seek"""
        if not self.verseek_head:
            raise VerseekError("no version to seek back to")

        self._checkout(basename(self.verseek_head))
        self.verseek_head = None

    def _seek_commit(self, commit: str) -> None:
        if not self.verseek_head:
            self.verseek_head = self.head

        self._checkout(commit)

    def seek_version(self, version: str | None = None) -> None:
        """Attempts to checkout a given version of this project"""
        if not version:
            self._seek_restore()
        else:
            versions = dict(self._list_versions())
            if version not in versions:
                raise VerseekError(f"no such version `{version}'")

            commit = versions[version]
            self._seek_commit(commit)


class GitSingle(Git):
    """version seeking class for git repository containing one package"""

    def __init__(self, path: AnyPath) -> None:
        Git.__init__(self, path)
        self.autoversion = Autoversion(fspath(path), precache=True)

    def _get_commit_datetime(self, commit: str) -> datetime.datetime:
        output = self.git.cat_file("commit", commit)
        m = re.search(r" (\d{10}) ", output)
        assert m is not None
        timestamp = int(m.group(1))
        return datetime.datetime.utcfromtimestamp(timestamp)

    def _create_changelog(
        self, version: str, entry_datetime: datetime.datetime
    ) -> None:
        release = "UNRELEASED"

        def parse_control(path: str) -> dict[str, str]:
            with open(path) as fob:
                lines = [
                    line.rstrip() for line in fob if not line.startswith(" ")
                ]
            return {
                k: v
                for (k, v) in [
                    re.split(r"\s*:\s*", line, maxsplit=1)
                    for line in lines
                    if line and ":" in line
                ]
            }

        control = parse_control(self.path_control)

        with LocaleAs(locale.LC_TIME, "C"):
            with open(self.path_changelog, "w") as fob:
                print(
                    f"{control['Source']} ({version}) {release}; urgency=low",
                    file=fob,
                )
                print(file=fob)
                print("  * undocumented", file=fob)
                print(file=fob)
                entry_datetime_str = entry_datetime.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000"
                )
                print(
                    f" --  {control['Maintainer']}  {entry_datetime_str}",
                    file=fob,
                )

    def seek_version(self, version: str | None = None) -> None:
        """Attempts to checkout a given version of this project"""
        if not version:
            if exists(self.path_changelog):
                os.remove(self.path_changelog)

            self._seek_restore()
        else:
            commit = self.autoversion.version2commit(version)
            self._seek_commit(commit)
            self._create_changelog(version, self._get_commit_datetime(commit))

    def list_versions(self) -> list[str]:
        """Returns a list of versions for this project"""
        branch = basename(self.verseek_head or self.head)

        commits = self.git.rev_list(branch)
        return [self.autoversion.commit2version(commit) for commit in commits]


def new(path: AnyPath) -> Base:
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


def list_versions(path: AnyPath) -> list[str]:
    """List versions of project found at path

    Args:
        path: path to project as any os.PathLike (including str, bytes,
              pathlib.Path, etc.)

    Returns:
        a list of versions as strings
    """
    return new(path).list_versions()


def seek_version(path: AnyPath, version: str | None = None) -> None:
    """Seek to <version> in Debian source package at <path>.
    If <version> is None, unseek.

    Note: how this is implemented depends on the path type.

    Args:
        path: path to project as any os.PathLike (including str, bytes,
              pathlib.Path, etc.)
    """
    return new(path).seek_version(version)
