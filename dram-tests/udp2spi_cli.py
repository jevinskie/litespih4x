#!/usr/bin/env python3

import socket
import sys

from rich import print

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('127.0.0.1', 2443)

get_icdode = bytes([0x9f, 0x00, 0x00, 0x00])

sent = sock.sendto(get_icdode, server_address)
assert sent == len(get_icdode)

rsp, srv = sock.recvfrom(2000)
assert len(rsp) == len(get_icdode)

print(f'get_idcode: {get_icdode.hex()} rsp: {rsp.hex()}')
