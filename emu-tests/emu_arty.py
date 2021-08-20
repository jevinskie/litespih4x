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

from liteeth.phy.mii import LiteEthPHYMII

from litespih4x.emu import FlashEmu, QSPISigs

# Bench SoC ----------------------------------------------------------------------------------------

class EmuSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(200e6), with_scope=False):
        platform = arty.Platform(variant='a7-100')

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteSPIH4X emu on Arty",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq, with_mapped_flash=False)

        # SPI Flash Emu  ---------------------------------------------------------------------------
        self.clock_domains.cd_spi = ClockDomain()

        # UART -------------------------------------------------------------------------------------
        self.add_uart('serial', baudrate=3_000_000)

        # Etherbone --------------------------------------------------------------------------------
        # self.submodules.ethphy = LiteEthPHYMII(
        #     clock_pads=self.platform.request("eth_clocks"),
        #     pads=self.platform.request("eth"))
        # self.add_etherbone(phy=self.ethphy, ip_address='192.168.100.100')

        qrs = QSPISigs(sclk=Signal(), rstn=None, csn=Signal(), si=Signal(), so=Signal(), wpn=Signal(), sio3=Signal())
        qes = QSPISigs(sclk=Signal(), rstn=None, csn=Signal(), si=Signal(), so=Signal(), wpn=Signal(), sio3=Signal())
        self.submodules.emu = emu = FlashEmu(qrs=qrs, qes=qes)

        # Jtagbone ---------------------------------------------------------------------------------
        self.add_jtagbone()
        # tell Vivado about the JTAG clock 40 MHz
        self.platform.add_period_constraint(self.jtagbone_phy.cd_jtag.clk, 25)
        # self.platform.add_platform_command(
        #     "create_clock -name jtag_clk -period 25 [get_pins -of [get_cells -hier * -filter {LIB_CELL =~ BSCAN*}] -filter {name =~ */U_ICON/*/DRCK}]"
        # )

        # scope ------------------------------------------------------------------------------------
        if with_scope:
            from litescope import LiteScopeAnalyzer
            # phy_sigs = self.jtag_phy._signals
            # hello_sigs = set(self.jtag_hello._signals)
            # hello_sigs.remove(self.jtag_hello.hello_code)
            # fsm_sigs = self.jtag_phy.tap_fsm.finalize()
            # fsm_sigs = self.jtag_phy.tap_fsm._signals + self.jtag_phy.tap_fsm.fsm._signals
            analyzer_signals = [
                # *phy_sigs,
                # *hello_sigs,
                # *fsm_sigs,
            ]
            self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                                                         depth=756,
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
    parser.add_argument("--scope",       action="store_true", help="Enable litescope")
    args = parser.parse_args()

    soc     = EmuSoC(with_scope=args.scope)
    builder = Builder(soc, csr_csv="csr.csv")
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
