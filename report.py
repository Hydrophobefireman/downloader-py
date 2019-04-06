from sys import stdout, stderr


def coerce_to_str(a):
    return a if isinstance(a, str) else f"{a}"


def to_screen(text: str) -> None:
    stdout.write(coerce_to_str(text))


def err_to_screen(text: str) -> None:
    stderr.write(coerce_to_str(text))


class Report:
    def __init__(self, i: bool = False):
        self.cli = i

    def report_init(self):
        return to_screen("[Info]Downloader started\n") if self.cli else None
