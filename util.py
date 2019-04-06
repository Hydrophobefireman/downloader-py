from os.path import realpath, dirname, isfile, getsize

script_loc = realpath(__file__)
script_dir = dirname(script_loc)


class MetaError(Exception):
    pass


def make_range_sizes(_size, rc: int = 3) -> list:
    """this abomination generates range request 
    headers depending on number of chunks we download
	 the file in
    """
    if isinstance(_size, str) and _size.isdigit():
        size = int(_size)
    else:
        if not isinstance(_size, int):
            return None
        size = _size
    if size <= 0:
        raise ValueError(f"Range Can't Be {size}")
    _part = size / rc
    part = int(_part)
    divides = part == _part  # number was divisible
    ret = []
    last = 0
    next = 0
    final = size - 1
    for i in range(1, rc + 1):
        next = (i * part) - (1 if divides else 0)
        n = final if i == rc else next  # in case of last iteration
        ret.append(
            {"range": f"bytes={last}-{n}", "size": n - last + 1, "from": last, "to": n}
        )
        last = n + 1
    return ret


def safe_getsize(f: str):
    #    if isfile(f):
    #   print(getsize(f))
    return getsize(f) if isfile(f) else 0


def force_round(n, i: int) -> str:
    return f"%.{i}f" % n
