"""Print an official MSX launch URL for a hosted synthetic-only startup root."""

import argparse
from urllib.parse import quote, urlsplit


def launch_url(root_url: str) -> str:
    url = urlsplit(root_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Use a public HTTPS URL for the synthetic startup root only")
    return (
        "https://msx.benzac.de/?start="
        + quote("content:" + root_url, safe="")
        + "&input=2&init=1&suspend=0&animate=0"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root_url", help="Public HTTPS location of msx_storage_start.json")
    args = parser.parse_args()
    print(launch_url(args.root_url))


if __name__ == "__main__":
    main()
