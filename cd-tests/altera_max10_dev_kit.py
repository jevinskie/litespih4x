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


class PHYSub(Module):
    def __init__(self):
        self.rx_cnt_phy_sub = Signal(8)
        self.sync.eth_rx += self.rx_cnt_phy_sub.eq(self.rx_cnt_phy_sub + 1)


class PHY(Module):
    def __init__(self):
        self.clock_domains.cd_eth_rx = ClockDomain()
        self.rx_cnt_phy = Signal(8)
        self.sync.eth_rx += self.rx_cnt_phy.eq(self.rx_cnt_phy + 1)
        self.submodules.physub = PHYSub()


class MACSub(Module):
    def __init__(self):
        self.rx_cnt_mac_sub = Signal(8)
        self.sync.eth_rx += self.rx_cnt_mac_sub.eq(self.rx_cnt_mac_sub + 1)

class MAC(Module):
    def __init__(self):
        self.clock_domains.cd_eth_rx = ClockDomain()
        self.rx_cnt_mac = Signal(8)
        self.sync.eth_rx += self.rx_cnt_mac.eq(self.rx_cnt_mac + 1)
        self.submodules.macsub = MACSub()

class FlashEmuMemTop(Module):
    def __init__(self):
        self.clock_domains.cd_sys = ClockDomain()
        self.sys_clk = Signal()
        self.comb += [
            ClockSignal("sys").eq(self.sys_clk),
        ]

        self.submodules.ethphy = PHY()
        # self.ethphy = ClockDomainsRenamer({"eth_rx": "ethphy_eth_rx"})(self.ethphy)
        self.submodules.ethphy1 = PHY()
        self.submodules.mac = MAC()
        self.mac =  ClockDomainsRenamer({"eth_rx": "ethphy_eth_rx"})(self.mac)


# Main ---------------------------------------------------------------------------------------------

def main():
    fmt = FlashEmuMemTop()



    r = verilog.convert(fmt,
                          {
                              fmt.sys_clk,
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
