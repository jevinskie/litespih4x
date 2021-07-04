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

from liteeth.phy.mii import LiteEthPHYMII
from liteeth.mac import LiteEthMAC
from liteeth.core.arp import LiteEthARP
from liteeth.core.ip import LiteEthIP
from liteeth.core.udp import LiteEthUDP
from liteeth.core.icmp import LiteEthICMP
from liteeth.core import LiteEthUDPIPCore
from liteeth.common import convert_ip

from litejtag_ext.hello import JTAGHello

# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(50e6)):
        platform = altera_max10_dev_kit.Platform()

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteJTAG Hello on Altera MAX10 Dev Kit",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # Ethernet ---------------------------------------------------------------------------------
        self.submodules.ethphy = LiteEthPHYMII(
            clock_pads = self.platform.request("eth_clocks"),
            pads       = self.platform.request("eth"),
            with_hw_init_reset = True)

        # Ethernet MAC
        self.submodules.ethmac = LiteEthMAC(phy=self.ethphy, dw=8,
                                            interface="crossbar",
                                            endianness=self.cpu.endianness,
                                            hw_mac=streamer_source_mac_address)

        # HW ethernet
        source_ip_int: int = convert_ip(streamer_source_ip_address)
        self.submodules.arp = LiteEthARP(self.ethmac, streamer_source_mac_address, source_ip_int, sys_clk_freq, dw=8)
        self.submodules.ip = LiteEthIP(self.ethmac, streamer_source_mac_address, source_ip_int, self.arp.table, dw=8)
        self.submodules.icmp = LiteEthICMP(self.ip, source_ip_int, dw=8)
        self.submodules.udp = LiteEthUDP(self.ip, source_ip_int, dw=8)

        udp_port = self.udp.crossbar.get_port(streamer_port, dw=8)
        self.submodules.streamer = Streamer(sys_clk_freq, streamer_target_ip_address, streamer_port, udp_port, bitrate=streamer_max_packet_size * 8 * 4)

        # JTAGbone ---------------------------------------------------------------------------------
        # self.add_jtagbone()

        # UARTbone ---------------------------------------------------------------------------------
        self.add_uartbone(baudrate=3_000_000)

        # scope ------------------------------------------------------------------------------------
        from litescope import LiteScopeAnalyzer
        analyzer_signals = [
            self.streamer.source.ready,
            self.streamer.source.valid,
            # self.streamer.streamer_conv,
            # self.streamer.udp_streamer,
            # self.streamer.pipeline,
            self.streamer.valid,
            # self.streamer.running_counter,
            self.streamer.toggle,
            # self.streamer.streamer_counter,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                                                     depth=256,
                                                     clock_domain="sys",
                                                     csr_csv="analyzer.csv")

        # Leds -------------------------------------------------------------------------------------
        from litex.soc.cores.led import LedChaser
        self.submodules.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Hello on Altera MAX10 Dev Kit")
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
