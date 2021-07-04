#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause


import os
import argparse

from migen import *

from litex_boards.platforms import digilent_arty as arty
from litex_boards.targets.digilent_arty import _CRG

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litejtag_ext.hello import JTAGHello
from litex.soc.cores.jtag import JTAGPHY, S7JTAG

# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(50e6)):
        platform = arty.Platform(variant='a7-100')

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteJTAG Hello on Arty",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, with_mapped_flash=False)

        # JTAG Hello -------------------------------------------------------------------------------
        self.clock_domains.cd_jtag = ClockDomain()
        self.submodules.jtag_phy = S7JTAG(chain=1)
        self.submodules.jtag_hello = JTAGHello(self.jtag_phy.drck, self.jtag_phy.reset, self.jtag_phy)

        # UARTBone ---------------------------------------------------------------------------------
        self.add_uartbone(baudrate=3_000_000)

        # scope ------------------------------------------------------------------------------------
        from litescope import LiteScopeAnalyzer
        phy_sigs = self.jtag_phy._signals
        hello_sigs = set(self.jtag_hello._signals)
        # hello_sigs.remove(self.jtag_hello.hello_code)
        analyzer_signals = [
            *phy_sigs,
            *hello_sigs,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                                                     depth=8192,
                                                     clock_domain="sys",
                                                     csr_csv="analyzer.csv")

        # LEDs -------------------------------------------------------------------------------------
        from litex.soc.cores.led import LedChaser
        self.submodules.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Hello on Arty")
    parser.add_argument("--build",       action="store_true", help="Build bitstream")
    parser.add_argument("--load",        action="store_true", help="Load bitstream")
    args = parser.parse_args()

    soc     = BenchSoC()
    builder = Builder(soc, csr_csv="csr.csv")
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
