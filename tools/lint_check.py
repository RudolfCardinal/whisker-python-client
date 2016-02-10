#!/usr/bin/env python

import os
from os.path import abspath, dirname, join, splitext
import shutil
import subprocess

CURRENT_DIR = dirname(abspath(__file__))
PROJECT_BASE_DIR = abspath(join(CURRENT_DIR, os.pardir))

FLAKE8 = shutil.which('flake8')
if not FLAKE8:
    raise AssertionError("Need flake8")

for dirpath, subdirs, files in os.walk(PROJECT_BASE_DIR):
    for f in files:
        filename, ext = splitext(f)
        if ext == '.py':
            filepath = join(dirpath, f)
            subprocess.call([FLAKE8, filepath])
