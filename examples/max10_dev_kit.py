#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause


import os
import argparse

from migen import *

from litex_boards.platforms import altera_max10_dev_kit
from litex_boards.targets.altera_max10_dev_kit import _CRG

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litejtag_ext.hello import JTAGHello
from litex.soc.cores.jtag import JTAGPHY, MAX10JTAG, JTAGTAPFSM

# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6)):
        platform = altera_max10_dev_kit.Platform()

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteJTAG Hello on MAX10",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # JTAG Hello -------------------------------------------------------------------------------
        self.platform.add_reserved_jtag_decls()
        self.clock_domains.cd_jtag = ClockDomain()
        rtms = self.platform.request("altera_reserved_tms")
        rtck = self.platform.request("altera_reserved_tck")
        rtdi = self.platform.request("altera_reserved_tdi")
        rtdo = self.platform.request("altera_reserved_tdo")

        # jc = self.cd_jtag.clk
        # print(jc)

        reserved_jtag_pads = Record([
                ('altera_reserved_tms', rtms),
                ('altera_reserved_tck', rtck),
                ('altera_reserved_tdi', rtdi),
                ('altera_reserved_tdo', rtdo),
            ],
            name='altera_jtag_reserved',
        )
        self.submodules.jtag_phy = MAX10JTAG(reserved_jtag_pads, chain=1)
        self.submodules.jtag_hello = JTAGHello(self.jtag_phy.drck, self.crg.cd_sys.rst, self.jtag_phy)
        self.submodules.jtag_tap_fsm = JTAGTAPFSM(self.jtag_phy.altera_reserved_tms, self.jtag_phy.altera_reserved_tck, self.crg.cd_sys.rst)

        # UARTBone ---------------------------------------------------------------------------------
        self.add_uartbone(baudrate=3_000_000)

        # scope ------------------------------------------------------------------------------------
        from litescope import LiteScopeAnalyzer
        phy_sigs = self.jtag_phy._signals
        phy_sigs.remove(self.jtag_phy.altera_reserved_tdo) # wont pass fitter, output must go to pin
        phy_sigs.remove(self.jtag_phy.tdocore)
        hello_sigs = set(self.jtag_hello._signals)
        # hello_sigs.remove(self.jtag_hello.hello_code)
        self.jtag_tap_fsm.fsm.finalize()
        fsm_sigs = self.jtag_tap_fsm._signals
        analyzer_signals = [
            *phy_sigs,
            *hello_sigs,
            *fsm_sigs,
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

    def finalize(self, *args, **kwargs):
        super().finalize(*args, **kwargs)
    #     self.platform.add_period_constraint('altera_reserved_tck', 1e9/50e6)
        # self.platform.add_period_constraint(self.platform.lookup_request('altera_reserved_tck', loose=True), 1e9/50e6)
        # self.platform.add_period_constraint(self.jtag_phy.tckutap, 1e9/35e6)
        # self.platform.add_period_constraint(self.jtag_phy.tckcore, 1e9/35e6)
        # self.platform.add_period_constraint(self.jtag_phy.drck, 1e9/35e6)

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Hello on MAX10")
    parser.add_argument("--build",       action="store_true", help="Build bitstream")
    parser.add_argument("--load",        action="store_true", help="Load bitstream")
    args = parser.parse_args()

    soc     = BenchSoC()
    builder = Builder(soc, csr_csv="csr.csv")
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".sof"))

if __name__ == "__main__":
    main()
