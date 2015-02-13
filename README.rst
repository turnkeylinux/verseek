Abstract interface for listing/accessing versions of Debian sources
===================================================================

Introduction
------------

Verseek, short for Version Seeker, is an abstract interface for
transparently listing and accessing versions of Debian source packages
regardless of the specific storage layer the package is contained in,
which is detected automatically.

I separated verseek from pool because I figured it would be easier to
develop/debug this layer separately, and also that users would
potentially benefit from having raw access to the provided
functionality.

Usage example
-------------

::

    $ verseek git/pyhello --list
    1.3
    1.2
    1.0

    $ verseek git/pyhello 1.2

    $ git/pyhello/pyhello
    hello world 1.2

    $ verseek git/pyhello

    $ git/pyhello/pyhello
    hello world 1.3

How it works
------------

It is useful to understand how verseek works, even if just in
principle, in order to understand the implications for managing source
versions under various storage types

Currently, verseek supports 4 types of underlying storage:

1) *plain directory*: may contain multiple source packages, but only the
   most current version can be accessed
2) *git*: a git repository potentially containing multiple Debian
   packages
3) *git-single*: a git repository containing only one auto-versioned
   Debian project
4) *sumo*: a Sumo arena potentially containing multiple Debian packages

Storage backend: plain directory
--------------------------------

This is the simplest storage layer, and it doesn't do much besides
satisfying verseek's interface. When you *list* versions available in
a plain directory, you'll only get the latest version, which is
determined by parsing debian/changelog. Accordingly, this is the only
version you can seek to.

Storage backend: git
--------------------

In addition to being a useful storage layer in itself, this also
happens to be the base type from which all other supported storage
layers inherit. I will later describe the derived layers in respect to
how they are different from the base type.

* Listing: version lists are calculated by

  1) listing all commits in which path/debian/changelog changes::

      git-rev-list <branch> path/debian/changelog

  2) for each commit, extracting the version by parsing debian/changelog in those commits::

      git-cat-file blob <commit>:path/debian/changelog

* Seeking: implemented by checking out the commit in which the changelog
  changed. Note that this checks out the entire git repository, so you
  can't seek to different versions of different packages in the same
  underlying git repository at the same time.

  Since verseek checks out a specific commit rather than a branch, Git
  will perform a *detached* checkout (HEAD is pointing directly to a
  commit), while the current branch is preserved in VERSEEK_HEAD.
                
Storage backend: git-single (derived from git)
----------------------------------------------

Changes relative to Git storage: Uses autoversioning rather than
revisions of debian/changelog to list versions and to map versions to
commits.  - After checking out the commit for a version, verseek creates
a dummy changelog. The *release* field in the changelog is controlled by
the *RELEASE* environment variable, and defaults to *UNRELEASED*.
        
Storage backend: Sumo arena
---------------------------

Changes relative to Git storage:

* Operates on an open arena union path. For example::

      $ verseek -l sumotest/arena/pyhello
      1.2
      1.1
      1.0

* We list commits in which debian/changelog changed *in the overlay*
  Note that this means verseek won't see debian/changelog revisions in
  the fat, so for example, if you want verseek to "see" the
  debian/changelog you unpacked from a tarball, you'll have to::
  
       touch arena/pyhello/debian/changelog
       
  This will perform a copy-on-write to the overlay.

* We use sumo-checkout instead of git-checkout. Under some conditions,
  sumo-checkout may need a network connection to retrieve uncached urls.
  Also note that locally generated thin branches will be checked out
  much more quickly than remote thin branches (for which the journal has
  to be replayed from the closest locally vailable fat commit).

Limitations
-----------

verseek expects debian/control to exist in any version of the source
package, because this is the file verseek uses to identify that a path
is indeed a debian source in the first place.

If you seek back to a version that does not have debian/control -
verseek will get stuck on that version, and you won't be able to seek to
another version with verseek because it won't even recognize the path as
a valid Debian package.  Note, that the arena has to be open.
