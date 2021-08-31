#!/usr/bin/env python3

#
# This file is part of LiteDRAM.
#
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse

from migen import *

from litex_boards.platforms import arty
from litex_boards.targets.digilent_arty import _CRG

from litex.soc.cores.clock import *
from litex.soc.interconnect.csr import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litedram.common import PHYPadsReducer
from litedram.phy import s7ddrphy
from litedram.modules import MT41K128M16

from liteeth.phy.mii import LiteEthPHYMII

from litespih4x.emu_dram import FlashEmuDRAM

# Bench SoC ----------------------------------------------------------------------------------------

class DRAMSoC(SoCCore):
    def __init__(self, uart="crossover", sys_clk_freq=int(200e6), with_bist=False, with_analyzer=False):
        platform = arty.Platform(variant='a7-100')

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
            ident               = "LiteSPIh4x dram test Arty",
            ident_version       = True,
            cpu_type            = "picorv32",
            cpu_variant         = "minimal",
            integrated_rom_size = 0x10000,
            integrated_rom_mode = "rw",
            uart_name           = uart)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        self.submodules.ddrphy = s7ddrphy.A7DDRPHY(
            pads         = PHYPadsReducer(platform.request("ddram"), [0, 1]),
            memtype      = "DDR3",
            nphases      = 4,
            cl           = 8,
            cwl          = 7,
            sys_clk_freq = sys_clk_freq)
        self.add_sdram("sdram",
            phy       = self.ddrphy,
            module    = MT41K128M16(sys_clk_freq, "1:4"),
            origin    = self.mem_map["main_ram"],
            with_bist = with_bist)

        self.trace_sig = trace_sig = Signal()
        self.dram_port = dram_port = self.sdram.crossbar.get_port(name="fdp", data_width=32)

        self.submodules.flash_dram = flash_dram = FlashEmuDRAM(dram_port, trace_sig)


        # UARTBone ---------------------------------------------------------------------------------
        # if uart != "serial":
        #     self.add_uartbone(name="serial", clk_freq=100e6, baudrate=3_000_000, cd="uart")

        # Etherbone --------------------------------------------------------------------------------
        # self.submodules.ethphy = LiteEthPHYMII(
        #     clock_pads = self.platform.request("eth_clocks"),
        #     pads       = self.platform.request("eth"),
        #     with_hw_init_reset = False)
        # self.add_etherbone(phy=self.ethphy)
        self.add_jtagbone()

        # Analyzer ---------------------------------------------------------------------------------
        if with_analyzer:
            from litescope import LiteScopeAnalyzer
            flash_dram.ctrl_fsm.finalize()
            analyzer_signals = \
                [self.ddrphy.dfi] + \
                flash_dram._signals + flash_dram.ctrl_fsm._signals + \
                flash_dram.port._signals + [flash_dram.port.cmd, flash_dram.port.rdata, flash_dram.port.wdata]
            self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                depth        = 256,
                clock_domain = "sys",
                register     = True,
                csr_csv      = "analyzer.csv")
            analyzer_trigger = self.analyzer.trigger.enable_d
            self.comb += trace_sig.eq(analyzer_trigger)

        # Leds -------------------------------------------------------------------------------------
        from litex.soc.cores.led import LedChaser
        self.submodules.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteDRAM Bench on Arty A7")
    parser.add_argument("--build",         action="store_true", help="Build bitstream")
    parser.add_argument("--with-bist",     action="store_true", help="Add BIST Generator/Checker")
    parser.add_argument("--with-analyzer", action="store_true", help="Add Analyzer")
    parser.add_argument("--load",          action="store_true", help="Load bitstream")
    args = parser.parse_args()

    soc     = DRAMSoC(with_bist=args.with_bist, with_analyzer=args.with_analyzer)
    builder = Builder(soc, output_dir="build/arty", csr_csv="csr.csv")
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
