#!/usr/bin/env python3
import sys
from pathlib import Path


def check_file(f: str):
    if not Path(f).is_file():
        print(f'file "{f}" does not exist')
        sys.exit(2)


def check_dir(f: str):
    if not Path(f).is_dir():
        print(f'dir "{f}" does not exist')
        sys.exit(2)


if __name__ == '__main__':
    check_file('.grablib.lock')
    check_dir('static')
    check_dir('static/libs/build_bootstrap.scss')
    check_dir('static/libs/js/jquery.js')
