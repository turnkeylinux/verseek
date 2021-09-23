#!/usr/bin/python3

from distutils.core import setup

setup(
    name="verseek",
    version="2.0rc1",
    author="Jeremy Davis",
    author_email="jeremy@turnkeylinux.org",
    url="https://github.com/turnkeylinux/verseek",
    packages=["verseek_lib"],
    scripts=["verseek"]
)
