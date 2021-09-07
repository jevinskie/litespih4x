#!/usr/bin/env python3

import argparse

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litex.soc.cores.uart import RS232PHYModel
from litex.soc.cores.spi import SimSPIMaster

from litedram.modules import MT41K128M16
from litedram import modules as litedram_modules
from litedram.modules import parse_spd_hexdump
from litedram.phy.model import sdram_module_nphases, get_sdram_phy_settings
from litedram.phy.model import SDRAMPHYModel

from liteeth.phy.model import LiteEthPHYModel

from litespih4x.emu_dram import FlashEmuDRAM

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
    ("serial2spi", 0,
        Subsignal("source_valid", Pins(1)),
        Subsignal("source_ready", Pins(1)),
        Subsignal("source_data",  Pins(8)),

        Subsignal("sink_valid",   Pins(1)),
        Subsignal("sink_ready",   Pins(1)),
        Subsignal("sink_data",    Pins(8)),
    ),
    ("spi", 0,
        Subsignal("clk",          Pins(1)),
        Subsignal("cs_n",         Pins(1)),
        Subsignal("mosi",         Pins(1)),
        Subsignal("miso",         Pins(1)),
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
    def __init__(self, sys_clk_freq = None, **kwargs):
        platform     = Platform()
        sys_clk_freq = int(sys_clk_freq)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
            ident         = "litespih4x dram test simulation",
            ident_version = True,
            cpu_type      = "None",
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # Trace ------------------------------------------------------------------------------------
        self.platform.add_debug(self, reset=0)

        # # DDR3 -------------------------------------------------------------------------------------
        # sdram_clk_freq = sys_clk_freq
        # sdram_module = MT41K128M16(sdram_clk_freq, "1:4")
        # sdram_settings = get_sdram_phy_settings(
        #     memtype=sdram_module.memtype,
        #     data_width=16,
        #     clk_freq=sdram_clk_freq,
        #     cl = 8,
        #     cwl = 7,
        # )
        # self.submodules.ddrphy = SDRAMPHYModel(
        #     module = sdram_module,
        #     settings = sdram_settings,
        #     data_width = 16,
        #     clk_freq = sdram_clk_freq,
        #     verbosity = 0,
        #     init = [],
        # )
        # self.add_sdram("sdram",
        #     phy       = self.ddrphy,
        #     module    = sdram_module,
        #     origin    = self.mem_map["main_ram"],
        #     l2_cache_size = 0,
        #     with_bist = True,
        # )


        self.submodules.spi_uart_phy = spi_uart_phy = RS232PHYModel(self.platform.request("serial2spi"))
        self.submodules.spi_uart_master = spi_uart_master = SimSPIMaster(
            self.spi_uart_phy,
            self.platform.request("spi"),
            sys_clk_freq,
            sys_clk_freq // 4,
        )

        # self.dram_port = dram_port = self.sdram.crossbar.get_port(name="fdp")

        self.trace_sig = trace_sig = Signal()
        # self.trace_sig = trace_sig = self.sim_trace.pin
        # self.submodules.flash_dram = flash_dram = FlashEmuDRAM(dram_port, trace_sig)

        # Reduce memtest size for simulation speedup
        self.add_constant("MEMTEST_DATA_SIZE", 8 * 1024)
        self.add_constant("MEMTEST_ADDR_SIZE", 8 * 1024)
        self.add_constant("CONFIG_DISABLE_DELAYS", 1)

        # Etherbone --------------------------------------------------------------------------------
        self.submodules.ethphy = LiteEthPHYModel(self.platform.request("eth"))
        self.add_etherbone(phy=self.ethphy, ip_address = "192.168.42.100", buffer_depth=16*4096-1)

        from litescope import LiteScopeAnalyzer

        # flash_dram.ctrl_fsm.finalize()
        analyzer_trigger = Signal()
        anal_enable = Signal()
        anal_hit = Signal()
        run_flag = Signal()


        analyzer_signals = list(set(
            # [self.ddrphy.dfi] + \
            # flash_dram._signals + flash_dram.ctrl_fsm._signals + \
            # flash_dram.port._signals + \
            # [flash_dram.port.cmd, flash_dram.port.rdata, flash_dram.port.wdata] + \
            [analyzer_trigger, anal_enable, anal_hit, run_flag] + \
            spi_uart_phy._signals_recursive + spi_uart_master._signals_recursive
        ))
        self.submodules.analyzer = LiteScopeAnalyzer(analyzer_signals,
                                                     depth=256,
                                                     clock_domain="sys",
                                                     csr_csv="analyzer.csv")
        # self.add_csr("analyzer")
        self.comb += run_flag.eq(self.analyzer.storage.run_flag)
        self.comb += analyzer_trigger.eq(run_flag)
        self.comb += anal_hit.eq(self.analyzer.trigger.hit)
        self.comb += anal_enable.eq(self.analyzer.trigger.enable.storage)
        self.comb += trace_sig.eq(analyzer_trigger | self.sim_trace.pin)
#
# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteEth Bench Simulation")
    parser.add_argument("--sys-clk-freq",         default=200e6,           help="System clock frequency (default: 200MHz)")
    parser.add_argument("--trace",                action="store_true",     help="Enable Tracing")
    parser.add_argument("--trace-cycles",         default=128,             help="Number of cycles to trace")
    parser.add_argument("--opt-level",            default="O3",            help="Verilator optimization level")
    parser.add_argument("--debug-soc-gen",        action="store_true",     help="Don't run simulation")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    sim_config = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=args.sys_clk_freq)
    sim_config.add_module("ethernet", "eth", args={"interface": "tap0", "ip": "192.168.42.100"})
    sim_config.add_module("serial2console", "serial")
    sim_config.add_module("serial2tcp", "serial2spi", args={"port": "2442", "bind_ip": "127.0.0.1"})

    soc_kwargs     = soc_core_argdict(args)
    builder_kwargs = builder_argdict(args)

    soc_kwargs['sys_clk_freq'] = int(args.sys_clk_freq)
    soc_kwargs['uart_name'] = 'sim'
    soc_kwargs['integrated_main_ram_size'] = 0
    # soc_kwargs['cpu_type'] = 'picorv32' # slow
    # soc_kwargs['cpu_variant'] = 'minimal'

    builder_kwargs['csr_csv'] = 'csr.csv'

    soc     = SimSoC(**soc_kwargs)
    if not args.debug_soc_gen:
        builder = Builder(soc, **builder_kwargs)
        for i in range(2):
            build = (i == 0)
            run   = (i == 1)
            builder.build(
                build=build,
                run=run,
                skip_sw_build=run,
                sim_config=sim_config,
                trace=args.trace,
                trace_cycles=args.trace_cycles,
                opt_level=args.opt_level,
            )

if __name__ == "__main__":
    main()
