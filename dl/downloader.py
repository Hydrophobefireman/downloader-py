import shutil
import sys
from os import remove
from os.path import basename, isfile, join, realpath
from threading import Thread as _Parallel_impl
from time import time
from typing import Union, Optional
from ._cache import get_cached_file, get_cachedir, make_cached_file
from .report import Report, to_screen
from .URL import URL, UA_d, basic_headers
from .util import force_round, make_range_sizes, safe_getsize, to_MB


class Downloader(object):
    """
    Downloader Class  
        Args:
            url (Union[URL, str]): the url to download
            ua (Optional[str], optional): User Agent to pass in the headers. Defaults to None.
            f (Optional[str], optional): Filename to save the file to. Defaults to None.
            d (Optional[str], optional): Directory to save the file in. Defaults to None.
            intermediate_fn (Optional[str], optional): Filename for the intermediate files created in the threads. Defaults to None.
            is_cli (Optional[bool], optional): Is CLI. Defaults to False.
            t (Optional[int], optional): Number of threads to run the download in. Defaults to 3.
            v (Optional[bool], optional): Verbosity. Defaults to False.
    """

    is_resumable: bool = False
    start_time: int = 0
    did_resume: bool = False
    report: bool = True
    _continued_size: int = 0

    def _verbose_logger(self, t: str, *args, **k):

        if not self._verb:
            return
        logger_map = {
            "INIT": lambda: "Init Downloader",
            "URL-RECEIVED": lambda u: f"Sanitized URL:{u}",
            "URL-REDIR": lambda u: f"After Redirect:{u}",
            "INIT-INFO": lambda ua, is_resumable, s_path, m_file: f"User agent:{ua}\n\
                [logger]resumable: {is_resumable}\n[logger]save path:{s_path}\n[logger]Meta filename:{m_file}",
        }
        fn = logger_map.get(t)
        if fn:
            return print("[logger]", fn(*args, **k) if args else fn(**k))

    def _make_file(self):
        """
        Internal method that combines all the temporary files into the final file
        Raises:
           ValueError: When the size of the intermediate files does not match the file size in the content-length headers
        """
        if self._downloaded_size != self.filesize:
            raise ValueError(
                f"Downloaded filesize ({to_MB(self._downloaded_size)})  does not match expected size of {to_MB(self.filesize)} MB"
            )
        c = self.threads
        with open(self.save_path, "wb") as wfd:
            for i in range(c):
                f = get_cachedir(f"{self.filename}.part.{i}")
                with open(f, "rb") as fd:
                    shutil.copyfileobj(fd, wfd, 1024 * 1024 * 10)
                remove(f)
        remove(get_cachedir(f"{self._meta_file_name}.data.json"))

    def _progress_callback(self, size: float, speed: float, perc: float):
        """Called Everytime the request receives a chunk of data and updates the screen
        
        Args:
            size (float): Current downloaded file size
            speed (float): Calculated speed of the download
            perc (float): Download Percentage
        """
        to_screen(
            f"\rSize: {to_MB(size)} MB Downloaded: {perc}% -- Speed: {speed} MB/s  "
        )
        sys.stdout.flush()

    @property
    def _elapsed_time(self):
        return time() - self.start_time

    @property
    def _downloaded_size(self):
        return sum(
            safe_getsize(get_cachedir(f"{self.filename}.part.{i}"))
            for i in range(self.threads)
        )

    def __init__(
        self,
        url: Union[URL, str],
        ua: Optional[str] = None,
        f: Optional[str] = None,
        d: Optional[str] = None,
        intermediate_fn: Optional[str] = None,
        is_cli: Optional[bool] = False,
        t: Optional[int] = 3,
        v: Optional[bool] = False,
    ):

        self._verb = v
        self._verbose_logger("INIT")
        self.__thread_count = t or 3
        self.url = URL(url)
        self._verbose_logger("URL-RECEIVED", str(self.url))
        self.url.follow_redirects()
        self._verbose_logger("URL-REDIR", str(self.url))
        self.user_agent = ua or UA_d
        self.is_cli = is_cli
        self.report = Report(is_cli)
        self.report.report_init()
        self.filesize = self.url.file_size
        self.is_resumable = (
            self.url._m_headers.get("accept-ranges", "").lower() == "bytes"
            and self.filesize
        )
        self._meta_file_name = self.url.get_filesafe_url()
        self.filename = intermediate_fn or self._meta_file_name
        save_path = f or (self.url.get_suggested_filename() or self.filename)
        self.save_path = join(d, basename(save_path)) if d else realpath(save_path)
        self._verbose_logger(
            "INIT-INFO",
            self.user_agent,
            self.is_resumable,
            self.save_path,
            self._meta_file_name,
        )
        if isfile(self.save_path):
            raise FileExistsError(f"Filename:{self.save_path} already exists")
        print(f"Filesize: {to_MB(self.filesize)} MB")

    def _generate_init_headers(self, thread_count: int) -> dict:
        """Generate initial headers for the download
        
        Args:
            thread_count (int): Number of threads to download the file in

        Returns:
            dict: headers for the download
        """

        req = []
        previous_range = 0
        range_headers = make_range_sizes(self.filesize, thread_count)
        for i in range_headers:
            req.append(
                {
                    "range": i["range"],
                    "from": i["from"],
                    "to": i["to"],
                    "file_index": previous_range,
                    "file_size": i["size"],
                }
            )
            previous_range += 1
        reqs = {"headers": basic_headers, "filename": self.filename, "reqs": req}
        make_cached_file(self._meta_file_name, reqs)
        return reqs

    def _download_handler(self, h: dict, file: str, idx: int):
        """file download handler,to be called in a thread
        
        Args:
            h (dict): Headers for the request
            file (str): filename for the partial file
            idx (int): partial file index
        """
        n = get_cachedir(f"{file}.part.{idx}")
        with open(n, "ab") as f:
            with self.url.fetch(headers=h, stream=True, refetch=True) as r:
                for c in r.iter_content(chunk_size=2048):
                    if c:
                        f.write(c)
                    if self.report:
                        elapsed = self._elapsed_time
                        size = self._downloaded_size
                        perc = force_round((size / self.filesize) * 100, 2)
                        speed = force_round(
                            ((size - self._continued_size) / (1024 * 1024)) / elapsed, 2
                        )
                        self._progress_callback(size, speed, perc)

    def _simple_fetch(self):
        """
        Downloader for when the server does not support partial downloads
        """
        to_screen("Only reporting size downloaded\n")
        with open(self.save_path, "wb") as f:
            with self.url.fetch(headers=basic_headers, stream=True, refetch=True) as r:
                for c in r.iter_content(chunk_size=2048):
                    if c:
                        f.write(c)
                        self._progress_callback(safe_getsize(self.save_path), 0, 0)

    def _spawn_downloaders(self, h: dict):
        """Spawn downloader threads
        
        Args:
            h (dict): range headers and filename
        """
        hdr = h["headers"]
        fn = h["filename"]
        th = []
        reqs = h["reqs"]
        for i in reqs:
            th.append(
                _Parallel_impl(
                    target=self._download_handler,
                    args=({**hdr, "range": i["range"]}, fn, i["file_index"]),
                )
            )
        try:
            for i in th:
                i.start()
            for i in th:
                i.join()
            self._is_completed = True
        except:
            pass

    def _alter_headers(self, data: dict) -> dict:
        """Alter headers for continued file downloads
        
        Args:
            data (dict): previous headers
        
        Returns:
            dict: new headers and filename
        """
        headers = data["headers"]
        previous_file = data["filename"]
        ranges = data["reqs"]
        ret = []
        self.threads = len(ranges)
        to_screen("Continuing File Download\n")
        for i in ranges:
            idx = i["file_index"]
            size = i["file_size"]
            completed = safe_getsize(get_cachedir(f"{previous_file}.part.{idx}"))
            self._continued_size += completed
            if completed >= size:
                to_screen("skipping")
                continue
            to_screen(
                f"Chunk number: {idx} \n completed : {to_MB(completed)} of {to_MB(size)} MB\n"
            )
            ret.append(
                {"range": f"bytes={i['from']+completed}-{i['to']}", "file_index": idx}
            )

        return {"headers": headers, "filename": previous_file, "reqs": ret}

    def start(self, thread_count: int = None):
        """Start the file download
        
        Args:
            thread_count (int, optional): number of threads to download the file in. Defaults to None.
        """
        self.start_time = time()
        self.threads = thread_count or self.__thread_count
        if self.is_resumable:
            headers_to_fetch = get_cached_file(self._meta_file_name)
            if headers_to_fetch:
                self._spawn_downloaders(self._alter_headers(headers_to_fetch))
            else:
                self._spawn_downloaders(self._generate_init_headers(self.threads))
            self._make_file()
        else:
            to_screen(f"Server at {self.url.host} does not support multi threading\n")
            self._simple_fetch()
