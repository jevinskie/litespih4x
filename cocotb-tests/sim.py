#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
import socket
import time
from typing import Final

from migen import *
from migen.fhdl import verilog

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

from pyftdi.jtag import *

import attr
from rich import inspect as rinspect

srv: Final = start_sim_server()
ext: Final = cocotb.external

usec = 1000
poweronper: Final = 10_000+50
# resetper = 300*usec
resetper: Final = 10_000

flash_offset: Final = 0x100000
word0: Final = 0x00000093
word1: Final = 0x00000193

Ftck_mhz: Final = 20
clkper_ns: Final = 1_000 / Ftck_mhz
tclk: Final = Timer(clkper_ns, units='ns')
tclkh: Final = Timer(clkper_ns/2, units='ns')
# IDCODE: Final = BitSequence('0000000110', msb=True, length=10)
# IDCODE: Final = BitSequence('0000000110')
# IDCODE: Final = BitSequence('0010')
IDCODE: Final = BitSequence('00010', msb=True)

async def tmr(ns: float) -> None:
    await Timer(ns, units='ns')

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("qspiflash", 0,
        Subsignal("sclk", Pins(1)),
        Subsignal("rst", Pins(1)),
        Subsignal("csn", Pins(1)),

        Subsignal("si_i", Pins(1)),
        Subsignal("si_o", Pins(1)),
        Subsignal("si_oe", Pins(1)),

        Subsignal("so_o", Pins(1)),
        Subsignal("so_i", Pins(1)),
        Subsignal("so_oe", Pins(1)),

        Subsignal("wp_i", Pins(1)),
        Subsignal("wp_o", Pins(1)),
        Subsignal("wp_oe", Pins(1)),

        Subsignal("sio3_i", Pins(1)),
        Subsignal("sio3_o", Pins(1)),
        Subsignal("sio3_oe", Pins(1)),
     ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self, toolchain="cocotb"):
        super().__init__("SIM", _io, toolchain=toolchain)


# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, toolchain="cocotb", dump=False, sim_debug=False, trace_reset_on=False, **kwargs):
        platform     = Platform(toolchain=toolchain)
        sys_clk_freq = int(1e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = "LiteJTAG cocotb Simulation",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clk"))


        self.qspi_pads = qp = self.platform.request("qspiflash")

        self.qspi_si_ts = sit = TSTriple()
        sit.i = qp.si_i
        sit.o = qp.si_o
        sit.oe = qp.si_oe

        self.qspi_so_ts = sot = TSTriple()
        sot.i = qp.so_i
        sot.o = qp.so_o
        sot.oe = qp.so_oe

        self.qspi_wp_ts = wpt = TSTriple()
        wpt.i = qp.wp_i
        wpt.o = qp.wp_o
        wpt.oe = qp.wp_oe

        self.qspi_sio3_ts = sio3t = TSTriple()
        sio3t.i = qp.sio3_i
        sio3t.o = qp.sio3_o
        sio3t.oe = qp.sio3_oe

        self.submodules.qspi_model = qspi_model = MacronixModel(self.platform, qp.sclk, self.crg.cd_sys.rst, qp.csn, sit, sot, wpt, sio3t)

        if dump:
            with open('qspi_model.v', 'w') as f:
                f.write(str(verilog.convert(self.qspi_model)))
            sys.exit(0)

        self.specials.vcddumper = CocotbVCDDumperSpecial()

        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)


# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Simulation")
    parser.add_argument("--build", default=True,  action="store_true",     help="Build simulation")
    genopts = parser.add_mutually_exclusive_group()
    genopts.add_argument("--run",   default=False, action="store_true",     help="Run simulation")
    genopts.add_argument("--dump",  default=False, action="store_true",     help="Dump module")
    parser.add_argument("--toolchain",            default="cocotb",        help="Simulation toolchain")
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


def xbits(n, hi, lo):
    return (n >> lo) & (2**(hi+1 - lo) - 1)

def fork_clk():
    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())

async def tick_si(dut, si: BitSequence) -> BitSequence:
    dut._log.info(f'tick_si {si} {int(si)} tck: {sigs.sclk.value}')
    so = BitSequence()
    sigs.csn <= 0
    await tclk
    for di in si:
        dut._log.info(f'tick_si bit {di}')
        sigs.si_i <= di
        await ReadOnly()
        assert sigs.sclk.value == 0
        await tclkh
        sigs.sclk <= 1
        so += BitSequence(sigs.so_o.value.value, length=1)
        await tclkh
        sigs.sclk <= 0
    sigs.csn <= 1
    await tclk
    await NextTimeStep()
    return so

tick_si_ext = cocotb.function(tick_si)

async def tick_so(dut, nbits: int) -> BitSequence:
    # dut._log.info(f'tick_tdo {nbits}')
    si = BitSequence(0, length=nbits)
    so = await tick_si(dut, si)
    return so

tick_so_ext = cocotb.function(tick_so)


@cocotb.test()
async def reset_tap(dut):
    fork_clk()

    sigs.sclk <= 0
    sigs.csn <= 1
    sigs.si_i <= 0
    sigs.so_i <= 0
    sigs.wp_i <= 1 # FIXME
    sigs.sio3_i <= 0

    sigs.rst <= 0
    sigs.srst <= 1
    await tclk
    sigs.rst <= 1
    sigs.srst <= 0
    await tclk
    await Timer(2000, units='us')
    # await Timer(2*poweronper, units='ns')
    await Timer(2*resetper, units='ns')
    sigs.rst <= 0
    sigs.srst <= 1
    await tclk
    await Timer(2*resetper, units='ns')
    print(f'at end of reset sclk: {sigs.sclk.value}')

@cocotb.test(skip=False)
async def read_idcode(dut):
    fork_clk()
    dut._log.info("Running read_idcode...")
    await tmr(2*clkper_ns)

    si = BitSequence(0x9f0000, msb=True)
    so = await tick_si(dut, si)
    dut._log.info(f"si: {si} so: {so}")

    await tmr(4*clkper_ns)
    dut._log.info("Running read_idcode...done")


if __name__ == "__main__":
    main()
