#!/usr/bin/python
"""Seek to available versions in Debian source package

If no <version> is specified, undo previous seek (restore state)

Options:
  -l --list   list seekable versions
  
"""
from os.path import *
import sys
import help
import getopt

import verseek

@help.usage(__doc__)
def usage():
    print >> sys.stderr, "Syntax: %s -l /path/to/debian-source" % sys.argv[0]
    print >> sys.stderr, "Syntax: %s /path/to/debian-source [ <version> ]" % sys.argv[0]

def fatal(s):
    print >> sys.stderr, "error: " + str(s)
    sys.exit(1)

def list(path):
    try:
        versions = verseek.list(path)
    except verseek.Error, e:
        fatal(e)
        
    for version in versions:
        print version

def seek(path, version):
    try:
        verseek.seek(path, version)
    except verseek.Error, e:
        fatal(e)
    
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l", ["list"])
    except getopt.GetoptError, e:
        usage(e)

    if not args:
        usage()

    srcpath = args[0]
    if not isdir(srcpath):
        fatal("no such directory `%s'" % srcpath)
        
    for opt, val in opts:
        if opt == '-h':
            usage()

        if opt in ('-l', '--list'):
            return list(srcpath)
            
    try:
        version = args[1]
        if version in ('-l', '--list'):
            return list(srcpath)
        
    except IndexError:
        version = None

    seek(srcpath, version)
    
if __name__=="__main__":
    main()

