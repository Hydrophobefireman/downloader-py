import re
from urllib.parse import (
    urlparse as _parse,
    parse_qs as _qsparse,
    urlunparse as _unparse,
    ParseResult,
    urljoin as _urljoin,
    unquote,
)
from os.path import splitext
from hashlib import new as new_hash_fn
from typing import Callable, Tuple, Union
from secrets import token_urlsafe
from .err import warn_requests, warn_refetch, warn_first_fetch, warn_no_hash
from .util import (
    basic_headers,
    _normalise_url,
    _abort_request_after,
    remove_quotes,
    mime_types,
    int_or_none,
)

try:
    import requests as req
except ImportError:
    warn_requests()


class URL:
    """Simple url class that implements requests method in it 
	and also has some other methods made available that allow
	 guessing mime types and file names
	"""

    has_meta_data: bool = False
    request = None
    _readonlyattrs: Tuple[str] = (
        "scheme",
        "netloc",
        "path",
        "params",
        "query",
        "fragment",
        "username",
        "password",
    )
    _attrmap: dict = {"host": "netloc", "proto": "scheme", "search": "query"}
    _after_request: Tuple[str] = (
        "apparent_encoding",
        "close",
        "connection",
        "content",
        "cookies",
        "elapsed",
        "encoding",
        "headers",
        "history",
        "is_permanent_redirect",
        "is_redirect",
        "iter_content",
        "iter_lines",
        "json",
        "links",
        "next",
        "ok",
        "raise_for_status",
        "raw",
        "reason",
        "request",
        "status_code",
        "text",
        "url",
    )

    def __setattr__(self, _attr, value):
        attr = self._attrmap.get(_attr, _attr)  # allows simple aliasing
        if attr in self._readonlyattrs:  # don't allow overwriting them
            raise Exception(f"Can not change readonly attribute: {attr}")
        object.__setattr__(self, attr, value)

    def __getattr__(self, _attr):
        attr = self._attrmap.get(_attr, _attr)
        if attr in self._readonlyattrs:
            return object.__getattribute__(self._parsed, attr)
        if self.request and attr in self._after_request:
            return object.__getattribute__(self.request, attr)
        raise AttributeError(f"URL object has no attribute: {attr}")

    @staticmethod
    def attempt_url_fix(u: str) -> str:
        """attempts to fix common mistakes while passing a url"""
        if isinstance(u, URL):
            return str(u)
        if u.startswith("//"):
            u = f"http{u}"
        p = _parse(u)
        if not p.scheme:
            u = f"http://{u}"
        elif "htttp" == p.scheme:
            u = "http:" + u[6:]
        return u.strip()

    @staticmethod
    def s_get_filesafe_url(_url, hashed: bool = True) -> str:
        """static method that either returns a sha1-hashed url string or a sanitized filename-safe url for saving in files"""
        url = str(_url)
        if hashed:
            return URL.s_get_url_hash(url)
        s = unquote(url).strip().replace(" ", "-")
        return re.sub(r"(?u)[^-\w.]", "-", s)

    def get_filesafe_url(self, hashed=True) -> str:
        return self.s_get_filesafe_url(self, hashed)

    @staticmethod
    def s_get_url_hash(_url, hash_method: str = "sha1") -> str:
        """returns hash of the given url..useful for creating intermediate files for different urls 
			[Example]
			 >>> get_url_hash("https://google.com","sha256")
			 >>>'05046f26c83e8c88b3ddab2eab63d0d16224ac1e564535fc75cdceee47a0938d'
        """
        url = str(_url)
        method: Callable[[str], str]
        try:
            method = new_hash_fn(hash_method)
        except ValueError:  # hashlib/platform doesn't support the method
            warn_no_hash(hash_method)
            method = new_hash_fn("sha1")
        method.update(url.encode())
        return method.hexdigest()

    def get_url_hash(self) -> str:
        return self.s_get_url_hash(self)

    def __init__(self, _u: str):
        self.session = req.Session()
        if not _u:
            raise ValueError("Cannot generate URL from a falsey value")
        u: str = self.attempt_url_fix(_u)
        self._parsed = _normalise_url(_parse(u))

    def __str__(self):
        return _unparse(self._parsed)

    def change_url_attr(self, _k: str, v) -> None:
        """used to change any readonly url attribute"""
        k = self._attrmap.get(_k, _k)
        if k not in self._readonlyattrs:
            raise Exception(f"cannot update attribute:{_k}")
        dc = self._parsed._asdict()
        dc[k] = v
        self._parsed = ParseResult(**dc)

    def __dir__(self):
        """extends the dir function to return urlparse attributes like host, path and request attributes"""
        d = object.__dir__(self)
        d.extend(self._readonlyattrs)
        d.extend(self._attrmap.keys())
        if self.request:
            d.extend(self._after_request)
        return d

    def fetch(
        self,
        _method: str = "get",
        refetch: bool = False,
        update_on_redirect: bool = True,
        **kwargs,
    ):
        """use requests library functions on the url
		accepts all kwargs that request takes"""
        if self.request and not refetch:
            warn_refetch(self)
        method = _method.lower()
        if not hasattr(req, method):
            raise Exception(f"Requests library does not support method {method}")
        res = getattr(self.session, method)(
            str(self),
            allow_redirects=True,
            headers=basic_headers if not "headers" in kwargs else kwargs.pop("headers"),
            **kwargs,
        )
        if update_on_redirect:
            self._parsed = _parse(res.url)
        self.request = res
        return res

    def update_url_meta_data(self) -> None:
        """Get general meta data about the url"""
        headers: dict
        url: str
        try:
            ret = req.head(str(self), headers=basic_headers, allow_redirects=True)
            ret.raise_for_status()
            headers, url = ret.headers, ret.url
        except:
            headers, url = _abort_request_after(str(self), 1500)
        self.has_meta_data = True
        self._m_headers = headers
        self._parsed = _parse(url)

    def _set_extension(self, name: str) -> str:
        fn = splitext(name)
        return fn[0] + self.file_extension

    def get_suggested_filename(self, get_random: bool = True):
        url_path = self.path
        search = self.search
        qs = _qsparse(search)
        if self.has_meta_data:
            f = self._m_headers.get("content-disposition")
            if f:
                return remove_quotes(f.split("filename=")[1])
            # highest priority given to content disposition
        has_fwd_slash = "/" in url_path
        if has_fwd_slash:
            spl = url_path.split("/")
            if len(spl):
                n = spl[-1]
                if n:
                    return self.s_get_filesafe_url(n, False)
        return self._set_extension(
            self.get_filesafe_url(
                (
                    qs.get("file")
                    or qs.get("filename")
                    or qs.get("download")
                    or token_urlsafe(10)
                )
            )
        )

    @property
    def file_extension(self):
        if not self.has_meta_data:
            return ".bin"
        ct = self._m_headers.get("content-type", "").lower().split(";")[0].strip()
        return mime_types.get(ct, ".bin")

    @property
    def file_size(self):
        return int_or_none(self._m_headers.get("content-length", 0))

    def follow_redirects(self,):
        self.update_url_meta_data()
        return str(self)

    def get_relative_url(self, rel: str):
        return URL(_urljoin(str(self), rel))

    def refetch(self, *args, **kwargs):
        if not self.request:
            warn_first_fetch(self)
        kwargs["refetch"] = True
        return self.fetch(*args, **kwargs)
