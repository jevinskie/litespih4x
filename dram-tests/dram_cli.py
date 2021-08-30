#!/usr/bin/env python3

import time

from litex import RemoteClient

from rich import print

def main():
    bus = RemoteClient()
    bus.open()

    fill = 0xdeadbeef
    # bus.write(0x4000aaa0+4*0, fill)
    # bus.write(0x4000aaa0+4*1, fill+1)
    # bus.write(0x4000aaa0+4*2, fill+2)
    # bus.write(0x4000aaa0+4*3, fill+3)
    bus.write(0x4000aaa0, [fill, fill+1, fill+2, fill+3])
    time.sleep(0.01)

    bus.regs.flash_dram_fill_addr.write(0xaaa0//4)
    bus.regs.flash_dram_rd_cnt.write(4)
    # bus.regs.flash_dram_fill_word.write(0xaa5500ff)

    time.sleep(0.01)
    bus.regs.sim_trace_enable.write(1)
    time.sleep(0.01)
    bus.regs.sim_trace_enable.write(0)
    rbw = bus.regs.flash_dram_readback_word.read()
    print(f'readback word: {rbw:d} 0x{rbw:x}')

    buf = bus.read(0x4000aaa0, 4)
    print(f'buf: {buf} buf[0]: {hex(buf[0])}')

if __name__ == '__main__':
    main()

