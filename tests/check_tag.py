#!/usr/bin/env python3
import os
import sys

from grablib.version import VERSION

git_tag = os.getenv('TRAVIS_TAG')
if git_tag:
    if git_tag != str(VERSION):
        print('✖ "TRAVIS_TAG" environment variable does not match grablib.version: "%s" vs. "%s"' % (git_tag, VERSION))
        sys.exit(1)
    else:
        print('✓ "TRAVIS_TAG" environment variable matches grablib.version: "{}"'.format(VERSION))
else:
    print('✓ "TRAVIS_TAG" not defined')
