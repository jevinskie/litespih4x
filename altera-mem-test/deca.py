#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause


import random
import os
import argparse

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer, AsyncClockMux


from litex_boards.platforms import terasic_deca
from litex_boards.targets.terasic_deca import _CRG

from litex.build.altera.common import AlteraAsyncResetSynchronizer, AlteraAsyncClockMux
from litex.build.altera.quartus import AlteraQuartusToolchain

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.gen.fhdl import verilog

from litespih4x.emu_mem import FlashEmuMem


def val4addr(addr: int) -> int:
    return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)


class FlashEmuMemTop(Module):
    def __init__(self):
        self.clock_domains.cd_sys = ClockDomain()
        # self.clock_domains.cd_spi = ClockDomain()
        self.sys_clk = Signal()
        self.sys_rst = Signal()
        # self.spi_clk = Signal()
        self.comb += [
            # self.sys_clk.eq(ClockSignal("sys")),
            # self.sys_rst.eq(ResetSignal("sys")),
            # self.spi_clk.eq(ClockSignal("spi")),
            ClockSignal("sys").eq(self.sys_clk),
            # ResetSignal("sys").eq(self.sys_rst),
            # ClockSignal("spi").eq(self.spi_clk),
        ]
        # self.submodules.fm = fm = FlashEmuMem(self.cd_sys, self.cd_spi, 0x100)
        # self.comb += fm.sel.eq(0)
        # self.fmp = fmp = fm.spiemu_port
        # self.lmp = lmp = fm.loader_port
        # self.comb += fmp.adr.eq(addr_next)
        sz = 32*1024
        self.mem = self.specials.mem = mem = Memory(8, sz, init=[random.randint(0, 255) for a in range(sz)], name='flash_mem')
        self.specials.port = mem.get_port(clock_domain='sys', write_capable=True)


# Main ---------------------------------------------------------------------------------------------

def main():
    fmt = FlashEmuMemTop()



    r = verilog.convert(fmt,
                          {
                              fmt.sys_clk,
                              fmt.sys_rst,
                              fmt.port.adr,
                              fmt.port.dat_r,
                              fmt.port.dat_w,
                              fmt.port.we,
                              # fmt.spi_clk,
                              # fmt.fm.sel,
                              # fmt.fm.spiemu_port.adr,
                              # fmt.fm.spiemu_port.dat_r,
                          },
                        name="fmt",

                        special_overrides = {
                              AsyncResetSynchronizer: AlteraAsyncResetSynchronizer,
                              AsyncClockMux: AlteraAsyncClockMux,
                          },
    )
    with open('fmt.v', 'w') as vf:
        vf.write(r.main_source)
    for dat_name in r.data_files:
        with open(dat_name, 'w') as df:
            df.write(r.data_files[dat_name])


if __name__ == "__main__":
    main()
