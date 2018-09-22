#!/usr/bin/env python
# whisker/exceptions.py

"""
===============================================================================

    Copyright (C) 2011-2018 Rudolf Cardinal (rudolf@pobox.com).

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

**Whisker exceptions.**

"""


class WhiskerCommandFailed(Exception):
    """
    Raised by :class:`whisker.api.WhiskerApi` if a Whisker immediate-socket
    command fails.
    """
    pass


class ImproperlyConfigured(Exception):
    """
    Whisker is improperly configured; normally due to a missing library.
    """
    pass


class ValidationError(Exception):
    """
    Exception to represent failure to validate user input.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message
