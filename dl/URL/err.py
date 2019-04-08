def warn_requests():
    return warn(
        "[Warning] No requests package found!\n \
you can install requests by using \n\t pip install -U requests\n\n \
all URL methods that require requests library will throw exceptions \
"
    )


def warn_refetch(url):
    return print(
        f"[Warning]The URL \"{str(url)[:50]}\" \
has already been refetched, if it was intentional, \
pass refetch=True or use 'URL.refetch'\n\
This warning is raised to prevent additional \
network requests in case of erroneous loops"
    )


def warn_first_fetch(url):
    return print(
        '[Warning]Thr url "{str(url)[:50]}" \
has never veen fetched before..did you mean to fetch it?'
    )


def warn_no_hash(hash_method):
    return print(
        f"[Warning] hashlib does not support the method {hash_method}...falling back to sha256"
    )
