#!/usr/bin/env python3

import time

from litex import RemoteClient

from rich import print

def main():
    bus = RemoteClient()
    bus.open()
    bus.regs.flash_dram_fill_addr.write(0xaaa0//4)
    bus.regs.flash_dram_fill_word.write(0xaa5500ff)
    bus.regs.sim_trace_enable.write(1)
    time.sleep(0.1)
    bus.regs.sim_trace_enable.write(0)

    buf = bus.read(0x4000aaa0, 4)
    print(f'buf: {buf}')

if __name__ == '__main__':
    main()

