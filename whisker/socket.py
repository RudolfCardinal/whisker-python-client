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


def socket_receive(sock, bufsize=BUFFERSIZE):
    # return socket.recv(bufsize)  # Python 2
    return sock.recv(bufsize).decode('ascii')  # Python 3


def socket_sendall(sock, data):
    # return socket.sendall(data)  # Python 2
    return sock.sendall(data.encode('ascii'))  # Python 3


def socket_send(sock, data):
    # return socket.send(data)  # Python 2
    return sock.send(data.encode('ascii'))  # Python 3
