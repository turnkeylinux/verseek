#!/usr/bin/python
"""Seek to available versions in Debian source package

If no <version> is specified, undo previous seek (restore state)

Options:
  -l    list seekable versions
  
"""
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

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l")
    except getopt.GetoptError:
        usage(e)

    if not args:
        usage()

    srcpath = args[0]
    for opt, val in opts:
        if opt == '-h':
            usage()

        if opt == '-l':
            return verseek.list(srcpath)

    try:
        version = args[1]
    except IndexError:
        version = None

    verseek.seek(srcpath, version)
    
if __name__=="__main__":
    main()

