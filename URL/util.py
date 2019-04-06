from urllib.parse import ParseResult
from os.path import realpath, dirname, join as _path_join
import requests
from json import load as json_load

script_loc = realpath(__file__)
script_dir = dirname(script_loc)
del dirname
del realpath

mime_types: dict
with open(_path_join(script_dir, "mimes.json")) as f:
    mime_types = json_load(f)


UA_m = "Mozilla/5.0 (Linux; Android 8.1.0; Pixel Build/OPM2.171019.029; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/68.0.3325.109 Mobile Safari/537.36"
UA_d = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3526.73 Safari/537.36"
basic_headers = {
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": UA_d,
    "Upgrade-Insecure-Requests": "1",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "dnt": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
}


def _abort_request_after(url: str, byte_len: int = 1024):
    sess = requests.Session()
    with sess.get(
        url, headers=basic_headers, allow_redirects=True, stream=True
    ) as chunk:
        for _ in chunk.iter_content(byte_len):
            headers, url = chunk.headers, chunk.url
            chunk.close()
    return (headers, url)


def _normalise_url(parsed, remove_frag: bool = True):
    d: dict = parsed._asdict()
    d["scheme"] = d["scheme"].lower()
    d["netloc"] = d["netloc"].lower()
    d["fragment"] = ""
    return ParseResult(**d)


def remove_quotes(s):
    if s is None or len(s) < 2:
        return s
    for quote in ('"', "'"):
        if s[0] == quote and s[-1] == quote:
            return s[1:-1]
    return s


def int_or_none(i: any):
    if isinstance(i, int):
        return i
    try:
        return int(i)
    except:
        return None
