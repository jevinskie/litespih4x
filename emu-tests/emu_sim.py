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
from litespih4x.emu import FlashEmu, QSPISigs, IDCODE

import cocotb
from cocotb.triggers import Timer, ReadWrite, ReadOnly, NextTimeStep
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ModifiableObject
from cocotb_bus.bus import Bus

from cocotbext.wishbone.driver import WishboneMaster
from cocotbext.wishbone.driver import WBOp

import attr
from rich import inspect as rinspect

from pyftdi.jtag import BitSequence

USE_RESET_PIN: Final = False

srv: Final = start_sim_server()
ext: Final = cocotb.external

Fsys_clk_mhz = 100
Fqspiclk_mhz: Final = 25

clkper_ns: Final = 1_000 / Fsys_clk_mhz
tclk: Final = Timer(clkper_ns, units='ns')
tclkh: Final = Timer(clkper_ns/2, units='ns')
tclk2: Final = Timer(clkper_ns*2, units='ns')

qclkper_ns: Final = 1_000 / Fqspiclk_mhz
qtclk: Final = Timer(qclkper_ns, units='ns')
qtclkh: Final = Timer(qclkper_ns/2, units='ns')
qtclk2: Final = Timer(qclkper_ns*2, units='ns')


# tRLRH_ns = 10 * 1_000
tRLRH_ns = 10
tRLRH: Final = Timer(2*tRLRH_ns, units='ns')

# tRHSL_ns = 10 * 1_000
tRHSL_ns = 10
tRHSL: Final = Timer(2*tRHSL_ns, units='ns')

# tREADY2_ROLL_ns = 40 * 1_000
tREADY2_ROLL_ns = 40
tREADY2_ROLL: Final = Timer(2*tREADY2_ROLL_ns, units='ns')

# tVSL_ns = 1500 * 1_000
tVSL_ns = 10
tVSL: Final = Timer(2*tVSL_ns, units='ns')

# tREADY2_W_ns = 40_000_000
tREADY2_W_ns = 40
tREADY2_W = Timer(2*tREADY2_W_ns, units='ns')

# tW_ns = 40_000_000
tW_ns = 40
tW = Timer(2*tW_ns, units='ns')

async def tmr(ns: float) -> None:
    await Timer(ns, units='ns')


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
        Subsignal("wpn", Pins(1)),
        Subsignal("sio3", Pins(1)),
    ),
    ("qspiflash_emu", 0,
        Subsignal("sclk", Pins(1)),
        Subsignal("rstn", Pins(1)),
        Subsignal("csn", Pins(1)),
        Subsignal("si", Pins(1)),
        Subsignal("so", Pins(1)),
        Subsignal("wpn", Pins(1)),
        Subsignal("sio3", Pins(1)),
    ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(SimPlatform):
    def __init__(self, toolchain="cocotb"):
        mname = Path(__file__).stem
        super().__init__(mname, _io, name=mname, toolchain=toolchain)


# Bench SoC ----------------------------------------------------------------------------------------

class BenchSoC(SoCCore):
    def __init__(self, toolchain="cocotb", dump=False, sim_debug=False, trace_reset_on=False, **kwargs):
        platform     = Platform(toolchain=toolchain)
        sys_clk_freq = int(1e6)

        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=sys_clk_freq,
            ident          = f"LiteSPIh4x cocotb {Path(__file__).stem}",
            ident_version  = True
        )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = crg = CRG(platform.request("sys_clk"), rst=platform.request("sys_rst"))


        self.qspi_pads_real = qr = self.platform.request("qspiflash_real")
        self.qpsi_real_sigs = qrs = QSPISigs.from_pads(qr)
        self.submodules.qspi_model = qm = MacronixModel(self.platform,
            qr.sclk, qr.rstn, qr.csn, qr.si, qr.so, qr.wpn, qr.sio3
        )


        self.qspi_pads_emu = qe = self.platform.request("qspiflash_emu")
        self.qpsi_emu_sigs = qes = QSPISigs.from_pads(qe)
        cds = crg.clock_domains
        self.qspi_emu = self.submodules.qspi_emu = FlashEmu(crg.cd_sys, qrs=qrs, qes=qes, sz_mbit=256, idcode=IDCODE)


        self.wb_sim_tap = wb_sim_tap = wishbone.Interface()
        self.add_wb_master(wb_sim_tap, 'wb_sim_tap')

        if dump:
            with open('dump.v', 'w') as f:
                f.write(str(verilog.convert(self.qspi_emu)))
            sys.exit(0)

        self.specials.vcddumper = CocotbVCDDumperSpecial()

        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)


# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tristate Simulation")
    parser.add_argument("--build", default=False,  action="store_true",     help="Build simulation")
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
    builder = Builder(soc, csr_csv="csr.csv", csr_json="csr.json", compile_software=False)
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

    print()


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
            'csn': getattr(t, nsl(p.csn)),
            'si': getattr(t, nsl(p.si)),
            'so': getattr(t, nsl(p.so)),
            'wpn': getattr(t, nsl(p.wpn)),
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

    flash_mem_region: Final = soc.csr.regions['qspi_emu_flash_mem']
    flash_mem_wb_base: Final = flash_mem_region.origin // (flash_mem_region.busword // 8)
    flash_mem_sel_region: Final = soc.csr.regions['qspi_emu']
    flash_mem_sel_ptr: Final = flash_mem_sel_region.origin // (flash_mem_sel_region.busword // 8)

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
    cocotb.fork(Clock(cocotb.top.sys_clk, clkper_ns, units="ns").start())


async def spi_txfr_start(dut, q: QSPISigs):
    dut._log.info('-- SPI BEGIN')
    # assert q.csn.value == 1
    q.csn <= 0
    # dut._log.info('-- BEGIN')
    await qtclk


async def spi_txfr_end(dut, q: QSPISigs):
    # assert q.csn.value == 0
    await qtclk
    q.csn <= 1
    # dut._log.info('-- BEGIN')
    dut._log.info('-- SPI END')
    await qtclk


async def tick_si(dut, q: QSPISigs, si: BitSequence, write_only=False) -> BitSequence:
    so = None
    if not write_only:
        so = BitSequence()
    for di in si:
        # dut._log.info(f'tick_si bit {di}')
        q.si <= di
        await ReadOnly()
        assert q.sclk.value == 0
        await qtclkh
        q.sclk <= 1
        if not write_only:
            so += BitSequence(q.so.value.value, length=1)
        await qtclkh
        q.sclk <= 0
    await NextTimeStep()
    return so


async def tick_so(dut, q: QSPISigs, nbits: int, write_only=False) -> BitSequence:
    # dut._log.info(f'tick_tdo {nbits}')
    si = BitSequence(0, length=nbits)
    so = await tick_si(dut, q, si, write_only=write_only)
    return so

def reset_soc_line(sigs: Sigs):
    sigs.clk <= 0
    sigs.rst <= 0

async def reset_soc(dut):
    reset_soc_line(sigs)

    await tclk

    sigs.rst <= 1

    await tclk

    sigs.rst <= 0

    await tclk

def reset_flash_lines(q: QSPISigs):
    q.sclk <= 0
    q.rstn <= 1
    q.csn <= 1
    q.si <= 0
    q.wpn <= 0

async def reset_flash(q: QSPISigs):
    reset_flash_lines(q)

    await tVSL

    q.rstn <= 0

    await tRLRH

    for i in range(5):
        q.sclk <= 1
        await qtclkh
        q.sclk <= 0
        await qtclkh

    q.rstn <= 1

    await tRHSL
    await tREADY2_ROLL

async def read_flash_spi(dut, q: QSPISigs, addr: int, sz: int):
    assert addr < 2**24
    cmd = BitSequence(0x03, msb=True, length=8) + BitSequence(addr, msb=True, length=24)
    await spi_txfr_start(dut, q)
    await tick_si(dut, q, cmd, write_only=True)
    so = await tick_so(dut, q, sz*8, write_only=False)
    await spi_txfr_end(dut, q)
    return so.tobytes(msb=True)

async def read_flash_wb(dut, addr: int, sz: int):
    sel_wr_on_res = await wb_bus.send_cycle([WBOp(flash_mem_sel_ptr, dat=1)])
    assert sel_wr_on_res[0].ack
    mem_ptr = flash_mem_wb_base + addr
    rd_buf = b''
    for i in range(sz):
        wb_rd_res = await wb_bus.send_cycle([WBOp(mem_ptr)])
        wb_rd_byte = wb_rd_res[0].datrd
        rd_buf += bytes([wb_rd_byte])
        mem_ptr += 1
    sel_wr_off_res = await wb_bus.send_cycle([WBOp(flash_mem_sel_ptr, dat=0)])
    assert sel_wr_off_res[0].ack
    return rd_buf

async def write_flash_wb(dut, addr: int, buf: bytes):
    sel_wr_on_res = await wb_bus.send_cycle([WBOp(flash_mem_sel_ptr, dat=1)])
    assert sel_wr_on_res[0].ack
    mem_ptr = flash_mem_wb_base + addr
    for i in range(len(buf)):
        wb_wr_res = await wb_bus.send_cycle([WBOp(mem_ptr, dat=buf[i])])
        assert wb_wr_res[0].ack
        mem_ptr += 1
    sel_wr_off_res = await wb_bus.send_cycle([WBOp(flash_mem_sel_ptr, dat=0)])
    assert sel_wr_off_res[0].ack

@cocotb.test()
async def initial_reset(dut):
    fork_clk()
    reset_soc_line(sigs)
    reset_flash_lines(sigs.qe)
    await reset_soc(dut)
    await reset_flash(sigs.qe)


@cocotb.test(skip=True)
async def read_wb_soc_id(dut):
    fork_clk()

    # dut._log.info(f'bus: {wb_bus}')
    soc_id = ''
    soc_id_region = soc.csr.regions['identifier_mem']
    soc_id_ptr = soc_id_region.origin // (soc_id_region.busword // 8)
    # dut._log.info(f'soc_id_ptr: {soc_id_ptr:x}')
    while True:
        wb_res = await wb_bus.send_cycle([WBOp(soc_id_ptr)])
        wb_chr = wb_res[0].datrd
        if wb_chr == 0:
            break
        soc_id += chr(wb_chr)
        soc_id_ptr += 1
    dut._log.info(f'soc_id: {soc_id}')
    assert 'LiteSPIh4x' in soc_id


@cocotb.test(skip=False)
async def read_flash_id(dut):
    fork_clk()
    cmd = BitSequence(0x9f, msb=True, length=8)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    flash_id = await tick_so(dut, sigs.qe, 3*8)
    await spi_txfr_end(dut, sigs.qe)
    dut._log.info(f'flash_id: {flash_id}')

@cocotb.test(skip=False)
async def read_first_four_bytes(dut):
    fork_clk()
    first_four_bytes = await read_flash_spi(dut, sigs.qe, 0x4, 4)
    dut._log.info(f'first_four_bytes: {first_four_bytes.hex()}')

@cocotb.test(skip=False)
async def read_first_four_bytes_wb(dut):
    fork_clk()
    first_four_bytes_wb = await read_flash_wb(dut, 0x4, 4)
    dut._log.info(f'first four bytes WB: {first_four_bytes_wb.hex()}')

@cocotb.test(skip=False)
async def read_first_four_bytes_again(dut):
    fork_clk()
    first_four_bytes = await read_flash_spi(dut, sigs.qe, 0x4, 4)
    dut._log.info(f'first_four_bytes again: {first_four_bytes.hex()}')

@cocotb.test(skip=False)
async def write_first_four_bytes_wb(dut):
    fork_clk()
    await write_flash_wb(dut, 0x4, buf=bytes.fromhex('aa5500ff'))

@cocotb.test(skip=False)
async def read_first_four_bytes_again_but_different(dut):
    fork_clk()
    first_four_bytes = await read_flash_spi(dut, sigs.qe, 0x4, 4)
    dut._log.info(f'first_four_bytes again but different: {first_four_bytes.hex()}')

@cocotb.test(skip=True)
async def enable_write(dut):
    fork_clk()

    cmd = BitSequence(0x06, msb=True, length=8)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    await spi_txfr_end(dut, sigs.qe)

    dut._log.info(f'enabled write mode')

@cocotb.test(skip=True)
async def read_status_wel(dut):
    fork_clk()
    status = None

    cmd = BitSequence(0x05, msb=True, length=8)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    so = await tick_so(dut, sigs.qe, 8, write_only=True)
    await spi_txfr_end(dut, sigs.qe)
    status = so

    dut._log.info(f'status WEL: {status}')

@cocotb.test(skip=True)
async def enable_quad_mode(dut):
    fork_clk()

    cmd = BitSequence(0x0140, msb=True, length=16)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    await spi_txfr_end(dut, sigs.qe)

    dut._log.info(f'enabled quad mode')

@cocotb.test(skip=True)
async def read_status_wip(dut):
    fork_clk()
    status = None

    cmd = BitSequence(0x05, msb=True, length=8)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    so = await tick_so(dut, sigs.qe, 8, write_only=True)
    await spi_txfr_end(dut, sigs.qe)
    status = so

    dut._log.info(f'status WIP: {status}')

@cocotb.test(skip=True)
async def read_status_qe(dut):
    fork_clk()
    status = None

    await tREADY2_W
    await tW

    cmd = BitSequence(0x05, msb=True, length=8)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    so = await tick_so(dut, sigs.qe, 8, write_only=True)
    await spi_txfr_end(dut, sigs.qe)
    status = so

    dut._log.info(f'status QE: {status}')

@cocotb.test(skip=True)
async def read_first_four_bytes_qmode(dut):
    fork_clk()
    first_four_bytes = None

    cmd = BitSequence(0x6b000004, msb=True, length=32)
    await spi_txfr_start(dut, sigs.qe)
    await tick_si(dut, sigs.qe, cmd, write_only=True)
    so = await tick_so(dut, sigs.qe, 4*8, write_only=True)
    await spi_txfr_end(dut, sigs.qe)
    # so2 = await tick_so(dut, sigs.qe, 8*3)
    # print(f'so: {so}')
    # print(f'so2: {so2}')
    first_four_bytes = so

    dut._log.info(f'first_four_bytes: {first_four_bytes}')


@cocotb.test(skip=True)
async def reset_flash_cnt(dut):
    fork_clk()
    await reset_flash(sigs.qe)

@cocotb.test(skip=True)
async def inc_flash_cnt(dut):
    fork_clk()
    await tick_so(dut, sigs.qe, 16, write_only=True)


if __name__ == "__main__":
    main()
