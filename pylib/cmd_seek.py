#!/usr/bin/python
"""Seek to specified version of a Debian source package

If no version is specified, undo previous seek (restore state).
"""
import sys
import help

@help.usage(__doc__)
def usage():
    print >> sys.stderr, "Syntax: %s /path/to/debian-source [ version ]" % sys.argv[0]

def fatal(s):
    print >> sys.stderr, "error: " + str(s)
    sys.exit(1)

def main():
    args = sys.argv[1:]
    if not args:
        usage()

    srcpath = args[0]
    try:
        version = args[1]
    except IndexError:
        version = None

    print "srcpath: " + srcpath
    print "version: " + `version`

if __name__=="__main__":
    main()

