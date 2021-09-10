#!/usr/bin/env python3

import socket
import time

from litex import RemoteClient

from rich import print

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('127.0.0.1', 2443)

def get_idcode_spi():
    get_icdode_buf = bytes([0x9f, 0x00, 0x00, 0x00])

    sent = sock.sendto(get_icdode_buf, server_address)
    assert sent == len(get_icdode_buf)
    rsp, srv = sock.recvfrom(2000)
    assert len(rsp) == len(get_icdode_buf)

    print(f'get_idcode: {get_icdode_buf.hex()} rsp: {rsp.hex()}')

def read_spi(addr: int, sz: int):
    read_buf = bytes([0x03]) + addr.to_bytes(3, 'big', signed=False) + bytes(sz)

    sent = sock.sendto(read_buf, server_address)
    assert sent == len(read_buf)
    rsp, srv = sock.recvfrom(2000)
    assert len(rsp) == len(read_buf)

    print(f'read_buf[:4]: {read_buf[:4].hex()} data: {rsp[4:].hex()}')

def main():
    bus = RemoteClient(with_sim_hack=True)
    bus.open()

    buf = bus.read(0x40000000 + 0xEDBEEF, 4)
    print(f'buf before: {buf} buf[0]: {hex(buf[0])}')

    fill = 0xdeadbeef
    fill_buf = [fill + i for i in range((0x100-0xC0)//2)]
    bus.write(0x40000000 + 0xEDBEC0, fill_buf)
    time.sleep(0.01)

    # bus.regs.flash_dram_fill_addr.write(0xaaa0//16)
    # bus.regs.flash_dram_rd_cnt.write(4-1)
    # bus.regs.flash_dram_readback_word.write(2**128-1)
    # rbw = bus.regs.flash_dram_readback_word.read()
    # print(f'readback word cleared: 0x{rbw:x}')
    # # bus.regs.flash_dram_fill_word.write(0xaa5500ff)
    #
    # bus.regs.flash_dram_go.write(1)
    # # time.sleep(0.01)
    # bus.regs.flash_dram_go.write(0)
    # rbw = bus.regs.flash_dram_readback_word.read()
    # print(f'readback word: {rbw:d} 0x{rbw:x}')

    buf = bus.read(0x40000000 + 0xEDBEEF, 4)
    print(f'buf: {buf} buf[0]: {hex(buf[0])}')

if __name__ == '__main__':
    main()

