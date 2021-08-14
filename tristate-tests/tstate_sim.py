#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
from pathlib import Path
import socket
import time
from typing import Final

from migen import *
from migen.fhdl import verilog
from migen.fhdl.specials import Special

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.cocotb import start_sim_server
from litex.build.sim.common import CocotbVCDDumperSpecial

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litespih4x.macronix_model import MacronixModel

import cocotb
from cocotb.triggers import Timer, ReadWrite, ReadOnly, NextTimeStep
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ModifiableObject


_TRISTATE_VERILOG_NAME: Final = 'TristateModuleHand.v'
_TRISTATE_VERILOG_PATH: Final = Path(__file__).parent.joinpath(_TRISTATE_VERILOG_NAME)

import attr
from rich import inspect as rinspect

srv: Final = start_sim_server()
ext: Final = cocotb.external

Ftck_mhz: Final = 20
clkper_ns: Final = 1_000 / Ftck_mhz
tclk: Final = Timer(clkper_ns, units='ns')
tclkh: Final = Timer(clkper_ns/2, units='ns')

async def tmr(ns: float) -> None:
    await Timer(ns, units='ns')


# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("qspiflash_real", 0,
        Subsignal("clk", Pins(1)),
        Subsignal("rst", Pins(1)),

        Subsignal("sio3", Pins(1)),

        # Subsignal("sio3_i", Pins(1)),
        # Subsignal("sio3_o", Pins(1)),
        # Subsignal("sio3_oe", Pins(1)),
     ),
    ("qspiflash_emu", 0,

        Subsignal("sio3", Pins(1)),

     # Subsignal("sio3_i", Pins(1)),
     # Subsignal("sio3_o", Pins(1)),
     # Subsignal("sio3_oe", Pins(1)),
     ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self, toolchain="cocotb"):
        super().__init__("tstate_sim", _io, name="tstate_sim", toolchain=toolchain)


# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, toolchain="cocotb", dump=False, sim_debug=False, trace_reset_on=False, **kwargs):
        platform     = Platform(toolchain=toolchain)
        sys_clk_freq = int(1e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteSPIh4x cocotb tristate sim",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))


        self.qspi_pads = qp = self.platform.request("qspiflash_real")
        self.rf_sio3_ts = rf_sio3_ts = TSTriple()
        self.specials += rf_sio3_ts.get_tristate(qp.sio3)

        if dump:
            with open('ts_model_genned.v', 'w') as f:
                f.write(str(verilog.convert(self.ts_model)))
            sys.exit(0)

        self.specials.vcddumper = CocotbVCDDumperSpecial()

        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)


# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tristate Simulation")
    parser.add_argument("--build", default=True,  action="store_true",     help="Build simulation")
    genopts = parser.add_mutually_exclusive_group()
    genopts.add_argument("--run",   default=False, action="store_true",    help="Run simulation")
    genopts.add_argument("--dump",  default=False, action="store_true",    help="Dump module")
    parser.add_argument("--toolchain",            default="cocotb",        help="Simulation toolchain")
    parser.add_argument("--trace",                action="store_true",     help="Enable Tracing")
    parser.add_argument("--trace-fst",            action="store_true",     help="Enable FST tracing (default=VCD)")
    parser.add_argument("--trace-start",          default="0",             help="Time to start tracing (ps)")
    parser.add_argument("--trace-end",            default="-1",            help="Time to end tracing (ps)")
    parser.add_argument("--trace-exit",           action="store_true",     help="End simulation once trace finishes")
    parser.add_argument("--sim-end",              default="-1",            help="Time to end simulation (ps)")
    parser.add_argument("--sim-debug",            action="store_true",     help="Add simulation debugging modules")
    parser.add_argument("--sim-top", default=None,                         help="Use a custom file for the top sim module")
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
    # sim_config.add_clocker("jtag_tck", freq_hz=1e6//16)

    soc     = BenchSoC(toolchain=args.toolchain, dump=args.dump, sim_debug=args.sim_debug, trace_reset_on=args.trace_start > 0 or args.trace_end > 0)
    builder = Builder(soc, csr_csv="csr.csv", compile_software=False)
    soc.ns = builder.build(
        sim_config  = sim_config,
        trace       = args.trace,
        trace_fst   = args.trace_fst,
        trace_start = args.trace_start,
        trace_end   = args.trace_end,
        trace_exit  = args.trace_exit,
        sim_end     = args.sim_end,
        sim_top     = args.sim_top,
        module      = sys.modules[__name__],
        soc         = soc,
        build       = args.build,
        run         = args.run,
    )

@attr.s(auto_attribs=True)
class Sigs:
    clk: ModifiableObject
    rst: ModifiableObject

    sclk: ModifiableObject
    srst: ModifiableObject
    csn: ModifiableObject

    si_i: ModifiableObject
    si_o: ModifiableObject
    si_oe: ModifiableObject


    so_i: ModifiableObject
    so_o: ModifiableObject
    so_oe: ModifiableObject

    wp_i: ModifiableObject
    wp_o: ModifiableObject
    wp_oe: ModifiableObject

    sio3_i: ModifiableObject
    sio3_o: ModifiableObject
    sio3_oe: ModifiableObject


sigs = None
soc = None
ns = None


def get_sig_dict(t, p):
    def helper(platform, soc, ns):
        def nol(sig: Signal) -> str:
            return sig.name_override

        def nsl(sig: Signal) -> str:
            return ns.pnd[sig]

        return {
            'clk': getattr(t, nol(soc.crg.cd_sys.clk)),
            'rst': getattr(t, nol(soc.crg.cd_sys.rst)),

            'sclk': getattr(t, nsl(p.sclk)),
            'srst': getattr(t, nsl(p.rst)),
            'csn': getattr(t, nsl(p.csn)),

            'si_i': getattr(t, nsl(p.si_i)),
            'si_o': getattr(t, nsl(p.si_o)),
            'si_oe': getattr(t, nsl(p.si_oe)),

            'so_i': getattr(t, nsl(p.so_i)),
            'so_o': getattr(t, nsl(p.so_o)),
            'so_oe': getattr(t, nsl(p.so_oe)),

            'wp_i': getattr(t, nsl(p.wp_i)),
            'wp_o': getattr(t, nsl(p.wp_o)),
            'wp_oe': getattr(t, nsl(p.wp_oe)),

            'sio3_i': getattr(t, nsl(p.sio3_i)),
            'sio3_o': getattr(t, nsl(p.sio3_o)),
            'sio3_oe': getattr(t, nsl(p.sio3_oe)),
        }

    return srv.root.call_on_server(helper)


if cocotb.top is not None:
    soc = srv.root.soc
    ns = srv.root.ns
    pads = soc.qspi_pads

    d = get_sig_dict(cocotb.top, pads)
    sigs = Sigs(**d)

def fork_clk():
    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())


@cocotb.test()
async def reset_tap(dut):
    fork_clk()


if __name__ == "__main__":
    main()
