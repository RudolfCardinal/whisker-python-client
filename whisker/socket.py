#!/usr/bin/env python
# whisker/socket.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

import re
import socket

from whisker.constants import BUFFERSIZE


def get_port(x):
    if type(x) is int:
        return x
    m = re.match(r"\D", x)  # search for \D = non-digit characters
    if m:
        port = socket.getservbyname(x, "tcp")
    else:
        port = int(x)
    return port


# In Python 3, we work with strings within the client code, and bytes
# to/from the socket. Translation occurs here:


def socket_receive(socket, bufsize=BUFFERSIZE):
    # return socket.recv(BUFFERSIZE)  # Python 2
    return socket.recv(BUFFERSIZE).decode('ascii')  # Python 3


def socket_sendall(socket, data):
    # return socket.sendall(data)  # Python 2
    return socket.sendall(data.encode('ascii'))  # Python 3


def socket_send(socket, data):
    # return socket.send(data)  # Python 2
    return socket.send(data.encode('ascii'))  # Python 3
