#!/usr/bin/env python3

"""
Smart quotes also transforms "--" to en dash, "---" to em dash, and "..."
to ellipsis. See http://docutils.sourceforge.net/docs/user/config.html

For RST title conventions, see
    http://docs.openstack.org/contributor-guide/rst-conv/titles.html

"""

import docutils
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
import os
from os.path import abspath, dirname, join
import shutil
import subprocess
import sys
import tempfile
if sys.version_info[0] < 3:
    raise AssertionError("Need Python 3")

PYTHON = sys.executable
CURRENT_DIR = dirname(abspath(__file__))
PROJECT_BASE_DIR = abspath(join(CURRENT_DIR, os.pardir))
DOC_DIR = join(PROJECT_BASE_DIR, 'doc')
BUILD_DIR = join(PROJECT_BASE_DIR, 'build')
DOCUTILS_DIR = abspath(join(dirname(abspath(docutils.__file__))))

CSS_LIST = [
    'html4css1.css',  # docutils
    join(DOC_DIR, 'stylesheets/voidspace.css'),  # local
]
STYLESHEET_DIRS = [  # see rst2html.py --help
    join(DOCUTILS_DIR, 'writers/html4css1'),
]
RST = join(DOC_DIR, 'README.rst')
PDF = join(BUILD_DIR, 'manual.pdf')

RST2HTML = shutil.which('rst2html.py')  # definitely not just 'rst2html'!
if RST2HTML is None:
    raise AssertionError('Need rst2html.py')
WKHTMLTOPDF = shutil.which('wkhtmltopdf')
if WKHTMLTOPDF is None:
    raise AssertionError('Need wkhtmltopdf')

# wkhtmltopdf is tricky:
# 1. I've not managed to get wkhtmltopdf to cope with images unless it has a
#    disk file, rather than stdin.
# 2. Also, the filename MUST end in '.html'.
# 3. Other filenames are interpreted relative to the file's location, not
#    the current directory.

def call(cmdargs, *args, **kwargs):
    logger.debug("command: {}".format(cmdargs))
    subprocess.call(cmdargs, *args, **kwargs)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    os.makedirs(BUILD_DIR, exist_ok=True)
    htmlfile = tempfile.NamedTemporaryFile(
        suffix='.html', dir=DOC_DIR, delete=False)
    print("""
Making documentation
- Source: {RST}
- Intermediary: {htmlfile}
- Destination: {PDF}
    """.format(
        RST=RST,
        htmlfile=htmlfile.name,
        PDF=PDF,
    ))
    args = [
        PYTHON, RST2HTML, RST,
        '--stylesheet-path={}'.format(",".join(CSS_LIST)),
        '--smart-quotes', 'yes',
    ]
    if STYLESHEET_DIRS:
        args.append('--stylesheet-dirs={}'.format(",".join(STYLESHEET_DIRS)))
    call(args, stdout=htmlfile)
    htmlfile.close()
    call([WKHTMLTOPDF, htmlfile.name, PDF])
    os.remove(htmlfile.name)
