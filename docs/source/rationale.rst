..  docs/source/rationale.rst

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

.. include:: include/include_isonum_symbols.rst

.. _Rationale:

Rationale
=========

Approaches to sockets and message passing
-----------------------------------------

Whisker allows a multitude of clients in a great many languages -- anything
that can "speak" down a TCP/IP port, such as C++, Visual Basic, Perl, and
Python.

Whisker uses two sockets, a **main** socket, through which the Whisker server
can send events unprompted, and an **immediate** socket, used for sending
commands/queries and receiving immediate replies with a one-to-one relationship
between commands (client |rarr| server) and responses (server |rarr| client).
Consequently, the client must deal with unpredictable events coming from the
server. It might also have to deal with some sort of user interface (UI) code
(and other faster things, like data storage).

C++
~~~

In C++/MFC, sockets get their own thread anyway, and the framework tries to
hide this from you. So the GUI and sockets coexists fairly happily. Many
Whisker tasks use C++, but it's not the easiest thing in the world.

Perl
~~~~

In Perl, I've used only a very basic approach with a manual message loop,
like this:

.. literalinclude:: demo/whisker_client_snippet.pl
    :language: perl

Python
~~~~~~

In Python, I've used the following approaches:

Manual event loop
:::::::::::::::::

You can use base socket code, and poll the main
socket for input regularly. Simple. But you can forget about
simultaneous UI. Like this:

.. literalinclude:::: ../../whisker/test_rawsockets.py
    :language: python

Non-threaded, event-driven
::::::::::::::::::::::::::

The Twisted library is great for this (https://twistedmatrix.com/). However:

-   Bits of it, like Tkinter integration, still don't support Python 3 fully
    (as of 2015-12-23), though this is not a major problem (it's easy to
    hack in relevant bits of Python 3 support).

-   Though it will integrate its event loop (reactor) with several GUI
    toolkits, e.g.
    http://twistedmatrix.com/documents/current/core/howto/choosing-reactor.html
    this can still fail; e.g. with Tkinter, if you open a system dialogue
    (such as the standard "Open File..." or "Save As..." dialogues), the
    Twisted reactor will stop and wait, which is no good.
    This is a much bigger problem.
    (More detail on this problem in my dev_notes.txt for the starfeeder
    project.)

-   So one could use Twisted with no user interaction during the task.

It looks, from the task writer's perspective, like this:

.. literalinclude:: ../../whisker/test_twisted.py
    :language: python

Multithreading
::::::::::::::

For multithreading we can use Qt (with the PySide bindings). In this approach,
the Whisker task runs in separate threads from the UI. This works well,
though is not without some complexity. The Qt interface is nice, and
can be fairly fancy. You have to be careful with database access if
using SQLite (which is not always happy in a multithreaded context).

Verdict for simple uses
:::::::::::::::::::::::

Use Twisted and avoid any UI code while the task is running.


Database access
---------------

Database backend
~~~~~~~~~~~~~~~~

There are distinct advantages to making SQLite the default, namely:

-   It comes with everything (i.e. no installation required);

-   Database can be copied around as single files.

On the downside, it doesn't cope with multithreading/multiuser access quite
as well as "bigger" databases like MySQL.

Users will want simple textfile storage as well.

Front end
~~~~~~~~~

The options for SQLite access include direct access:

    https://docs.python.org/3.4/library/sqlite3.html

and SQLAlchemy:

    http://www.sqlalchemy.org/

Getting fancier, it's possible to manage database structure migrations with
tools like Alembic (for SQLAlchemy), but this may be getting too complicated
for the target end user.

However, the other very pleasantly simple front-end is dataset:

    https://dataset.readthedocs.org/en/latest/


User interface
--------------

A GUI can consume a lot of programmer effort. Let's keep this minimal or
absent as the general rule; for more advanced coding, the coder can do
his/her own thing (a suggestion: Qt).


Task configuration
------------------

Much of the GUI is usually about configuration. So let's get rid of all
that, because we're aiming at very simple programming here. Let's just
put config in a simple structure like JSON or YAML, and have the user edit it
separately.

JSON
~~~~

An example program:

.. literalinclude:: demo/json_config_example.py
    :language: python

The JSON looks like:

.. literalinclude:: demo/json_config_demo.json
    :language: json

YAML with attrdict
~~~~~~~~~~~~~~~~~~

This can be a bit fancier in terms of the object structure it can represent,
a bit cleaner in terms of the simplicity of the config file, and safer in terms
of security from dodgy config files.

Using an AttrDict allows a cleaner syntax for reading/writing the Python
object.

.. literalinclude:: demo/yaml_config_example.py
    :language: python

The YAML looks like this:

.. literalinclude:: demo/yaml_config_demo.yaml
    :language: yaml

A quick YAML tutorial
:::::::::::::::::::::

A key:value pair looks like:

.. code-block:: yaml

    key: value

A list looks like:

.. code-block:: yaml

    list:
        - value1
        - value2
        # ...

A dictionary looks like:

.. code-block:: yaml

    dict:
        key1: value1
        key2: value2
        # ...


Verdict for simple uses
~~~~~~~~~~~~~~~~~~~~~~~

Use YAML with AttrDict.

Package distribution
--------------------

This should be via PyPI, so users can just do:

.. code-block:: bash

    pip3 install whisker

.. code-block:: python

    from whisker import *  # but better actual symbols than "*"!
