#!/usr/bin/env python3

import time

from litex import RemoteClient

from rich import print

def main():
    bus = RemoteClient()
    bus.open()

    buf = bus.read(0x4000aaa0, 4)
    print(f'buf before: {buf} buf[0]: {hex(buf[0])}')

    fill = 0xdeadbeef
    fill_buf = [fill + i for i in range(16)]
    bus.write(0x4000aaa0, fill_buf)
    time.sleep(0.01)

    bus.regs.flash_dram_fill_addr.write(0xaaa0//16)
    bus.regs.flash_dram_rd_cnt.write(4-1)
    bus.regs.flash_dram_readback_word.write(2**128-1)
    rbw = bus.regs.flash_dram_readback_word.read()
    print(f'readback word cleared: 0x{rbw:x}')
    # bus.regs.flash_dram_fill_word.write(0xaa5500ff)

    bus.regs.flash_dram_go.write(1)
    # time.sleep(0.01)
    bus.regs.flash_dram_go.write(0)
    rbw = bus.regs.flash_dram_readback_word.read()
    print(f'readback word: {rbw:d} 0x{rbw:x}')

    buf = bus.read(0x4000aaa0, 4)
    print(f'buf: {buf} buf[0]: {hex(buf[0])}')

if __name__ == '__main__':
    main()

