#!/usr/bin/env/python

"""
whisker/__init__.py

===============================================================================

    Copyright © 2011-2020 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of the Whisker Python client library.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

The mere existence of this file makes Python treat the directory as a package.

"""

import logging

# Create whisker.__version__:
# noinspection PyPep8Naming
from whisker.version import VERSION as __version__

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
# http://eric.themoritzfamily.com/learning-python-logging.html
# http://stackoverflow.com/questions/12296214/python-logging-with-a-library-namespaced-packages  # noqa
