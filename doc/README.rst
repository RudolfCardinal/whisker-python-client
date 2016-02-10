.. For RST help, see http://www.sphinx-doc.org/en/stable/rest.html

.. include:: symbols/isonum.txt

===============================================================================
whisker
===============================================================================

Python package for Whisker clients.

- Whisker is a TCP/IP-based research control software suite.
  See http://www.whiskercontrol.com/

Author/licensing
===============================================================================

By Rudolf Cardinal.
Copyright |copy| 2016 Rudolf Cardinal.
See LICENSE.txt.

Range of approaches
===============================================================================

Whisker allows a multitude of clients in a great many languages -- anything
that can "speak" down a TCP/IP port, such as C++, Visual Basic, Perl, and
Python.

Sockets and message passing
===============================================================================

Whisker uses two sockets, a "main" socket, through which the Whisker server
can send events unprompted, and an "immediate" socket, used for sending
commands/queries and receiving immediate replies with a one-to-one
relationship between commands (client |rarr| server) and responses (server |rarr|
client). Consequently, the client must deal with unpredictable events
coming from the server. It might also have to deal with some sort of user
interface (UI) code (and other faster things, like data storage).

C++
---

In C++/MFC, sockets get their own thread anyway, and the framework tries to
hide this from you. So the GUI and sockets coexists fairly happily.

Perl
----

In Perl, I've tried only a very basic approach with a manual message loop,
like this:

.. include:: whisker_client_snippet.pl
    :code: perl

Python
------

In Python, I've tried the following approaches:

Manual event loop
~~~~~~~~~~~~~~~~~
You can use base socket code, and poll the main
socket for input regularly. Simple. But you can forget about
simultaneous UI. Like this:

.. include:: whisker_plain_socket_example.py
    :code: python

Non-threaded, event-driven
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Twisted library is great for this (https://twistedmatrix.com/). However:

-   It still doesn't support Python 3 fully (as of 2016-02-09), after
    several years, though this is not a major problem (it's easy to
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

-   So one could use Twisted with a bit of hacking and no user
    interaction.

It looks, from the task writer's perspective, like this:

.. include:: whisker_twisted_example.py
    :code: python

Multithreading
~~~~~~~~~~~~~~

For multithreading we can use Qt (with the PySide bindings). In this approach,
the Whisker task runs in separate threads from the UI. This works well,
though is not without some complexity. The Qt interface is nice, and
can be fairly fancy. You have to be careful with database access if
using SQLite (which is not always happy in a multithreaded context).

Verdict for simple uses
~~~~~~~~~~~~~~~~~~~~~~~

Use Twisted and avoid any UI code while the task is running.


Database access
===============================================================================

Database backend
----------------

There are distinct advantages to making SQLite the default, namely:

-   It comes with everything (i.e. no installation required);

-   Database can be copied around as single files.

On the downside, it doesn't cope with multithreading/multiuser access quite
as well as "bigger" databases like MySQL.

Users will want simple textfile storage as well.

Front end
---------

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
===============================================================================

A GUI can consume a lot of programmer effort. Let's keep this minimal or
absent as the general rule; for more advanced coding, the coder can do
his/her own thing (a suggestion: Qt).


Task configuration
===============================================================================

Much of the GUI is usually about configuration. So let's get rid of all
that, because we're aiming at very simple programming here. Let's just
put config in a simple structure like JSON or YAML, and have the user edit it
separately.

JSON
----

An example program:

.. include:: json_config_example.py
    :code: python

The JSON looks like:

.. include:: json_config_demo.json
    :code: json

YAML with attrdict
------------------

This can be a bit fancier in terms of the object structure it can represent,
a bit cleaner in terms of the simplicity of the config file, and safer in terms
of security from dodgy config files.

Using an AttrDict allows a cleaner syntax for reading/writing the Python
object.

.. include:: yaml_config_example.py
    :code: python

The YAML looks like this:

.. include:: yaml_config_demo.yaml
    :code: yaml

Verdict for simple uses
~~~~~~~~~~~~~~~~~~~~~~~

Use YAML with AttrDict.

Package distribution
===============================================================================

This should be via PyPI, so users can just do:

.. code:: python

    pip3 install whisker

    # ...

    from whisker import ...

Simple task
===============================================================================

Having done :code:`pip install whisker`, you should be able to do this:

.. include:: demo_config.yaml
    :code: yaml

.. include:: demo_simple_whisker_client.py
    :code: python
