#!/usr/bin/env python3

import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litedram.modules import MT41K128M16
from litedram import modules as litedram_modules
from litedram.modules import parse_spd_hexdump
from litedram.phy.model import sdram_module_nphases, get_sdram_phy_settings
from litedram.phy.model import SDRAMPHYModel

from liteeth.phy.model import LiteEthPHYModel

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("serial", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
    ("eth_clocks", 0,
        Subsignal("tx", Pins(1)),
        Subsignal("rx", Pins(1)),
    ),
    ("eth", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        SimPlatform.__init__(self, "SIM", _io)

# Bench SoC ----------------------------------------------------------------------------------------

class SimSoC(SoCCore):
    def __init__(self, **kwargs):
        platform     = Platform()
        sys_clk_freq = int(1e6)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
            ident         = "litespih4x dram test simulation",
            ident_version = True,
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # DDR3 -------------------------------------------------------------------------------------
        sdram_clk_freq = int(100e6)  # FIXME: use 100MHz timings
        sdram_module = MT41K128M16(sdram_clk_freq, "1:4")
        self.submodules.ddrphy = SDRAMPHYModel(
            module = sdram_module,
            data_width = 32,
            clk_freq = sdram_clk_freq,
            verbosity = 0,
            init = [],
        )
        self.add_sdram("sdram",
            phy       = self.ddrphy,
            module    = sdram_module,
            origin    = self.mem_map["main_ram"],
            l2_cache_size = 0,
            with_bist = True,
        )

        # Reduce memtest size for simulation speedup
        self.add_constant("MEMTEST_DATA_SIZE", 8 * 1024)
        self.add_constant("MEMTEST_ADDR_SIZE", 8 * 1024)

        # Etherbone --------------------------------------------------------------------------------
        self.submodules.ethphy = LiteEthPHYModel(self.platform.request("eth"))
        self.add_etherbone(phy=self.ethphy, ip_address = "192.168.42.100", buffer_depth=255)

        # Trace ------------------------------------------------------------------------------------
        platform.add_debug(self, reset=1)

# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteEth Bench Simulation")
    parser.add_argument("--trace",                action="store_true",     help="Enable Tracing")
    parser.add_argument("--trace-cycles",         default=128,             help="Number of cycles to trace")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    sim_config = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=1e6)
    sim_config.add_module("ethernet", "eth", args={"interface": "tap0", "ip": "192.168.42.100"})
    sim_config.add_module("serial2console", "serial")

    soc_kwargs     = soc_core_argdict(args)
    builder_kwargs = builder_argdict(args)

    soc_kwargs['uart_name'] = 'sim'
    soc_kwargs['integrated_main_ram_size'] = 0

    builder_kwargs['csr_csv'] = 'csr.csv'

    soc     = SimSoC(**soc_kwargs)
    builder = Builder(soc, **builder_kwargs)
    builder.build(sim_config=sim_config, trace=args.trace, trace_cycles=args.trace_cycles)

if __name__ == "__main__":
    main()
