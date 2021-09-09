#!/usr/bin/env python3

import socket
import sys

from rich import print

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('127.0.0.1', 2443)

def get_idcode():
    get_icdode_buf = bytes([0x9f, 0x00, 0x00, 0x00])

    sent = sock.sendto(get_icdode_buf, server_address)
    assert sent == len(get_icdode_buf)
    rsp, srv = sock.recvfrom(2000)
    assert len(rsp) == len(get_icdode_buf)

    print(f'get_idcode: {get_icdode_buf.hex()} rsp: {rsp.hex()}')

def read(addr: int, sz: int):
    read_buf = bytes([0x03]) + addr.to_bytes(3, 'big', signed=False) + bytes(sz)

    sent = sock.sendto(read_buf, server_address)
    assert sent == len(read_buf)
    rsp, srv = sock.recvfrom(2000)
    assert len(rsp) == len(read_buf)

    print(f'read_buf[:4]: {read_buf[:4].hex()} data: {rsp[4:].hex()}')

# get_idcode()

# read(0x4, 4)
read(0xEDBEEF, 4)
