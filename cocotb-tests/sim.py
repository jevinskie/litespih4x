#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
import sys
from typing import Final

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.cocotb import start_sim_server, stop_sim_server

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litejtag_ext.hello import TickerZeroToMax, BeatTickerZeroToMax, JTAGHello

from litejtag_ext import data as data_mod
from importlib_resources import files
_MOHOR_TAP_VERILOG_NAME: Final = 'window-packing.json'
_MOHOR_TAP_VERILOG_PATH: Final = files(data_mod).joinpath(_MOHOR_TAP_VERILOG_NAME)

import cocotb
from cocotb.triggers import Timer

sim_server = start_sim_server()

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("ticker_zero_to_max", 0,
        Subsignal("tick", Pins(1)),
        Subsignal("counter", Pins(32)),
    ),
    ("ticker_zero_to_max_from_freq", 0,
        Subsignal("tick", Pins(1)),
        Subsignal("counter", Pins(32)),
    ),
    ("beat_ticker", 0,
        Subsignal("tick", Pins(1)),
        Subsignal("tick_a", Pins(1)),
        Subsignal("counter_a", Pins(32)),
        Subsignal("tick_b", Pins(1)),
        Subsignal("counter_b", Pins(32)),
    ),
    ("jtag_clk", 0, Pins(1)),
    ("jtag_rst", 0, Pins(1)),
    ("jtag_hello", 0,
        Subsignal("tck", Pins(1)),
        Subsignal("tms", Pins(1)),
        Subsignal("tdi", Pins(1)),
        Subsignal("tdo", Pins(1)),
        Subsignal("reset", Pins(1)),
        Subsignal("drck", Pins(1)),
        Subsignal("shift", Pins(1)),
        Subsignal("sel", Pins(1)),
     ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self):
        super().__init__("SIM", _io, toolchain="cocotb")


# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, sim_debug=False, trace_reset_on=False, **kwargs):
        platform     = Platform()
        sys_clk_freq = int(1e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteJTAG cocotb Simulation",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))

        # Ticker A
        self.submodules.ticker_a = TickerZeroToMax(self.platform.request("ticker_zero_to_max"), max_cnt=15)
        # Ticker B
        self.submodules.ticker_b = BeatTickerZeroToMax(self.platform.request("beat_ticker"), max_cnt_a=5, max_cnt_b=7)
        # JTAG Hello
        jtag_pads = self.platform.request("jtag_hello")
        jtag_clk = self.platform.request("jtag_clk")
        jtag_rst = self.platform.request("jtag_rst")
        self.submodules.jtag_hello = JTAGHello(jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, jtag_pads.tdo,
                  self.crg.cd_sys.rst, jtag_pads)
        self.comb += jtag_pads.shift.eq(1)

        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)


# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Simulation")
    parser.add_argument("--trace",                action="store_true",     help="Enable Tracing")
    parser.add_argument("--trace-fst",            action="store_true",     help="Enable FST tracing (default=VCD)")
    parser.add_argument("--trace-start",          default="0",             help="Time to start tracing (ps)")
    parser.add_argument("--trace-end",            default="-1",            help="Time to end tracing (ps)")
    parser.add_argument("--trace-exit",           action="store_true",     help="End simulation once trace finishes")
    parser.add_argument("--sim-end",              default="-1",            help="Time to end simulation (ps)")
    parser.add_argument("--sim-debug",            action="store_true",     help="Add simulation debugging modules")
    args = parser.parse_args()
    try:
        args.trace_start = int(args.trace_start)
    except:
        args.trace_start = int(float(args.trace_start))
    try:
        args.trace_end = int(args.trace_end)
    except:
        args.trace_end = int(float(args.trace_end))

    sim_config = SimConfig()
    sim_config.add_clocker("sys_clk", freq_hz=1e6)
    sim_config.add_clocker("jtag_clk", freq_hz=1e6//16)

    soc     = BenchSoC(sim_debug=args.sim_debug, trace_reset_on=args.trace_start > 0 or args.trace_end > 0)
    builder = Builder(soc, csr_csv="csr.csv", compile_software=False)
    builder.build(
        sim_config  = sim_config,
        trace       = args.trace,
        trace_fst   = args.trace_fst,
        trace_start = args.trace_start,
        trace_end   = args.trace_end,
        trace_exit  = args.trace_exit,
        sim_end     = args.sim_end,
        module      = sys.modules[__name__],
    )


@cocotb.test()
async def read_idcode(dut):
    dut._log.info("Running read_idcode...")

    dut._log.info("Running read_idcode...done")


if __name__ == "__main__":
    print(f'__name__ was indeed __main__ args: {sys.argv}')
    main()

# stop_sim_server(sim_server)
