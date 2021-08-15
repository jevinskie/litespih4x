#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import time
from typing import Final

from migen import *
from migen.fhdl import verilog
from migen.fhdl.specials import Special

from litex.build.generic_platform import *
from litex.build.sim.platform import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.cocotb import start_sim_server
from litex.build.sim.common import CocotbVCDDumperSpecial

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone

from litespih4x.macronix_model import MacronixModel
from litespih4x.emu import FlashEmu

import cocotb
from cocotb.triggers import Timer, ReadWrite, ReadOnly, NextTimeStep
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ModifiableObject
from cocotb_bus.bus import Bus

from cocotbext.wishbone.driver import WishboneMaster
from cocotbext.wishbone.driver import WBOp

import attr
from rich import inspect as rinspect

srv: Final = start_sim_server()
ext: Final = cocotb.external

Ftck_mhz: Final = 20
clkper_ns: Final = 1_000 / Ftck_mhz
tclk: Final = Timer(clkper_ns, units='ns')
tclkh: Final = Timer(clkper_ns/2, units='ns')
tclk2: Final = Timer(clkper_ns*2, units='ns')

async def tmr(ns: float) -> None:
    await Timer(ns, units='ns')

SigObj = Signal
if cocotb.top is not None:
    SigObj = ModifiableObject

@attr.s(auto_attribs=True)
class QSPISigs:
    sclk: SigObj
    rstn: SigObj
    csn: SigObj
    si: SigObj
    so: SigObj
    wp: SigObj
    sio3: SigObj

    @classmethod
    def from_pads(cls, pads: Record) -> QSPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    ("qspiflash_real", 0,
        Subsignal("sclk", Pins(1)),
        Subsignal("rstn", Pins(1)),
        Subsignal("csn", Pins(1)),
        Subsignal("si", Pins(1)),
        Subsignal("so", Pins(1)),
        Subsignal("wp", Pins(1)),
        Subsignal("sio3", Pins(1)),
     ),
    ("qspiflash_emu", 0,
        Subsignal("sclk", Pins(1)),
        Subsignal("rstn", Pins(1)),
        Subsignal("csn", Pins(1)),
        Subsignal("si", Pins(1)),
        Subsignal("so", Pins(1)),
        Subsignal("wp", Pins(1)),
        Subsignal("sio3", Pins(1)),
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
        self.submodules.crg = CRG(platform.request("sys_clk"), rst=platform.request("sys_rst"))


        self.qspi_pads_real = qr = self.platform.request("qspiflash_real")
        qspi_sigs = QSPISigs.from_pads(qr)
        print(f'qspi_sigs: {qspi_sigs}')
        self.submodules.qspi_model = qm = MacronixModel(self.platform, qr.sclk, qr.rstn, qr.csn, qr.si, qr.so, qr.wp, qr.sio3)


        self.qspi_pads_emu = qe = self.platform.request("qspiflash_emu")

        self.wb_sim_tap = wb_sim_tap = wishbone.Interface()
        self.add_wb_master(wb_sim_tap, 'wb_sim_tap')

        if dump:
            with open('dump.v', 'w') as f:
                f.write(str(verilog.convert(self)))
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

    qr: QSPISigs
    qe: QSPISigs

sigs = None
soc = None
ns = None


def nol(sig: Signal) -> str:
    return sig.name_override


def nsl(sig: Signal) -> str:
    return ns.pnd[sig]

def get_qspisigs_dict(t, p):
    def helper(platform, soc, ns):
        return {
            'sclk':  getattr(t, nsl(p.sclk)),
            'rstn':  getattr(t, nsl(p.rstn)),
            'csn': getattr(t, nsl(p.rstn)),
            'si': getattr(t, nsl(p.si)),
            'so': getattr(t, nsl(p.so)),
            'wp': getattr(t, nsl(p.wp)),
            'sio3': getattr(t, nsl(p.sio3)),
        }
    return srv.root.call_on_server(helper)

def get_sigs_dict(t):
    def helper(platform, soc, ns):
        return {
            'clk':  getattr(t, nol(soc.crg.cd_sys.clk)),
            'rst':  getattr(t, nol(soc.crg.cd_sys.rst)),
        }
    return srv.root.call_on_server(helper)


if cocotb.top is not None:
    soc = srv.root.soc
    ns = srv.root.ns
    pads_real = soc.qspi_pads_real
    pads_emu = soc.qspi_pads_emu

    d = get_sigs_dict(cocotb.top)
    d['qr'] = QSPISigs(**get_qspisigs_dict(cocotb.top, pads_real))
    d['qe'] = QSPISigs(**get_qspisigs_dict(cocotb.top, pads_emu))
    sigs = Sigs(**d)

    wb_bus = WishboneMaster(cocotb.top, "wb_sim_tap", sigs.clk,
                          width=32,   # size of data bus
                          timeout=10, # in clock cycle number
                          signals_dict={"cyc":   "cyc",
                                        "stb":   "stb",
                                        "we":    "we",
                                        "adr":   "adr",
                                        "datwr": "dat_w",
                                        "datrd": "dat_r",
                                         "ack":  "ack" })

def fork_clk():
    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())


@cocotb.test()
async def reset_tap(dut):
    fork_clk()

    sigs.clk <= 0
    sigs.rst <= 0

    await tclk2

    sigs.rst <= 1

    await tclk2

    sigs.rst <= 0

    await tclk2


@cocotb.test(skip=True)
async def read_wb_soc_id(dut):
    fork_clk()

    dut._log.info(f'bus: {wb_bus}')
    soc_id = ''
    soc_id_region = soc.csr.regions['identifier_mem']
    soc_id_ptr = soc_id_region.origin // (soc_id_region.busword // 8)
    dut._log.info(f'soc_id_ptr: {soc_id_ptr:x}')
    while True:
        wb_res = await wb_bus.send_cycle([WBOp(soc_id_ptr)])
        wb_chr = wb_res[0].datrd
        if wb_chr == 0:
            break
        soc_id += chr(wb_chr)
        soc_id_ptr += 1
    dut._log.info(f'soc_id: {soc_id}')
    assert 'LiteSPIh4x' in soc_id



if __name__ == "__main__":
    main()
