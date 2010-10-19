import os
from utils import getoutput

class Error(Exception):
    pass

def chdir_path(method):
    def wrapper(path, *args):
        orig_cwd = os.getcwd()
        
        os.chdir(path)
        try:
            ret = method(*args)
        finally:
            os.chdir(orig_cwd)

        return ret
        
    return wrapper

@chdir_path
def _autoversion(*args):
    if not args:
        return None

    results = getoutput("autoversion", *args)
    if results is None:
        raise Error("autoversion failed: path=%s args=%s" % (`os.getcwd()`, `args`))

    return results.split("\n")

@chdir_path
def _git_rev_list_all():
    results = getoutput("git-rev-list", "--all")
    if results is None:
        raise Error("git-rev-list --all failed at path=%s" % (`os.getcwd()`))

    return results.split("\n")

def get_all_versions(path):
    """Use autoversion to get all versions at <path>"""
    commits = _git_rev_list_all(path)
    versions = _autoversion(path, *commits)

    return versions

# singular
def commit2version(path, commit):
    return  _autoversion(path, commit)[0]

def version2commit(path, version):
    return _autoversion(path, "-r", version)[0]

# plural
def commits2versions(path, commits):
    versions = _autoversion(path, *commits)
    return versions

def versions2commits(path, versions):
    commits = _autoversion(path, "-r", *versions)
    return commits
