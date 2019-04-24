from dl import Downloader


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Download Files in Multiple threads")
    parser.add_argument("url", metavar="URL", type=str, nargs="+")
    parser.add_argument("--ua", metavar="User Agent")
    parser.add_argument("-f", metavar="Output  Filename")
    parser.add_argument("-d", metavar="Output directory")
    parser.add_argument("-t",type=int,metavar="thread count")
    args = parser.parse_args()
    url = args.url[0]
    out_dir = args.d
    user_agent = args.ua
    filen = args.f
    Downloader(url, ua=user_agent, f=filen, d=out_dir,t=args.t).start()
