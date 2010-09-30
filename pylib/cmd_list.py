#!/usr/bin/python
"""List versions of Debian source package
"""
import sys
import help

@help.usage(__doc__)
def usage():
    print >> sys.stderr, "Syntax: %s /path/to/debian-source" % sys.argv[0]

def fatal(s):
    print >> sys.stderr, "error: " + str(s)
    sys.exit(1)

def main():
    args = sys.argv[1:]
    if not args:
        usage()

    srcpath = args[0]
    print "srcpath: " + srcpath

if __name__=="__main__":
    main()

