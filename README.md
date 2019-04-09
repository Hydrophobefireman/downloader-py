# File downloader

A python based file downloader that can download chunks of file in parallel and supports resume (if the **file host** supports it)

It is modular and can be easily plugged into and extended for projects involving file downloads

# Usage

## Direct usage:

### Step 1:
clone the repo
```git clone https://github.com/Hydrophobefireman/downloader-py```

### Step 2:
```
python download.py "$url"
 ```
 the program will try to guess the filename and extension by checking  `content-disposition`  headers, and the URL.
 
 Or you could provide your file name by passing it through `-f`
 
 By default it uses a desktop chrome user agent but you can change it by passing a user agent string through `--ua`
 
 download directory can be set by setting `-d`

***
## Using the Downloader in your python app:

The api is small and simple enough and can be easily used for downloading files in  python apps.

You could do something like this:
```python
from dl import Downloader as d
def download_file(url:str)->None:
    file = d(url,f="path/to/file.txt")
    file.start(thread_count=4)
    # the thread count determines the number of intermediate files to be created, 4 threads means 4 parallel requests   
```
***
by default the progress is not reported using a bar, but textual information is displayed,
to change that behavior you can extend the `_progress_callback`  method

```python
from dl import Downloader
class ProgressBarDownloader(Downloader):
    def _progress_callback(
        self, downloaded_size: float, 
              download_speed: float, 
              download_percent: float
    ):
      ...do something with the arguments
    # self._elapsed_time can also be accessed to find the time taken

```

The downloader also uses a  small URL based (micro-) library(?) 
that normalises url strings and attaches useful methods like `url.fetch()` to it.
 

## TODO:
Allow passing cookies for authenticated file downloads
