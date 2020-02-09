..  docs/source/usage.rst

..  Copyright © 2011-2020 Rudolf Cardinal (rudolf@pobox.com).
    .
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    .
        http://www.apache.org/licenses/LICENSE-2.0
    .
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


Usage
=====

There are three styles of Whisker client available. Full worked examples are
provided, along with a rationale for their use; see :ref:`Rationale`. The
outlines, however, look like these:

Twisted client (preferred for simple interfaces)
------------------------------------------------

.. code-block:: python

    from twisted.internet import reactor
    from whisker.twistedclient import WhiskerTwistedTask

    class MyWhiskerTask(WhiskerTwistedTask):
        # ...

    w = MyWhiskerTask()
    w.connect(...)
    reactor.run()

Qt client (preferred for GUI use)
---------------------------------

More complex; see the Starfeeder project example.

Raw socket client (deprecated)
------------------------------

.. code-block:: python

    from whisker.rawsocketclient import WhiskerRawSocketClient

    w = WhiskerRawSocketClient()
    w.connect_both_ports(...)
    # ...
    for line in w.getlines_mainsocket():
        # ...
