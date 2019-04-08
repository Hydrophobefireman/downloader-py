"""
Stuff for cached and temp files
"""

from os import mkdir as _i_mkdir
from os.path import join as _join, isfile as _isfile, isdir as _isdir
from .util import script_dir, MetaError
from json import load as _load, dump as _dump


cached_dir = _join(script_dir, ".cache")


def get_cachedir(f: str):
    mkdir(cached_dir)
    g = _join(cached_dir, f)
    return g


def make_cached_file(fn: str, data: dict, cd=cached_dir):
    _path = _join(cd, fn)
    file = f"{_path}.data.json"
    mkdir(cd)
    with open(file, "w") as f:
        _dump(data, f)


def get_cached_file(fn, cd=cached_dir):
    file = f"{_join(cd,fn)}.data.json"
    if not _isfile(file):
        return None
    with open(file) as f:
        try:
            return _load(f)
        except Exception as e:
            print(e)
            return None


def mkdir(x: str):
    if _isdir(x):
        return False
    _i_mkdir(x)
    return True
