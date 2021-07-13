#!/usr/bin/env python3

# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
import sys
from typing import Final

from migen import *

from litex.build.generic_platform import *
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig
from litex.build.sim.cocotb import start_sim_server
from litex.build.sim.common import CocotbVCDDumperSpecial

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litejtag_ext.hello import TickerZeroToMax, BeatTickerZeroToMax, JTAGHello
from litejtag_ext.mohor_tap import MohorJTAGTAP
from litejtag_ext.tap import JTAGTAP
from litex.soc.cores.jtag import JTAGTAPFSM

import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase

from pyftdi.jtag import *

import attr
from rich import inspect as rinspect

srv: Final = start_sim_server()
ext: Final = cocotb.external

Ftck_mhz: Final = 20
clkper_ns: Final = 1_000 / Ftck_mhz
IDCODE: Final = BitSequence('0010')

async def tmr(ns: float) -> None:
    await Timer(ns, units='ns')

# IOs ----------------------------------------------------------------------------------------------

_io = [
    ("sys_clk", 0, Pins(1)),
    ("sys_rst", 0, Pins(1)),
    # ("ticker_zero_to_max", 0,
    #     Subsignal("tick", Pins(1)),
    #     Subsignal("counter", Pins(32)),
    # ),
    # ("ticker_zero_to_max_from_freq", 0,
    #     Subsignal("tick", Pins(1)),
    #     Subsignal("counter", Pins(32)),
    # ),
    # ("beat_ticker", 0,
    #     Subsignal("tick", Pins(1)),
    #     Subsignal("tick_a", Pins(1)),
    #     Subsignal("counter_a", Pins(32)),
    #     Subsignal("tick_b", Pins(1)),
    #     Subsignal("counter_b", Pins(32)),
    # ),
    # ("jtag_clk", 0, Pins(1)),
    # ("jtag_rst", 0, Pins(1)),
    ("jtag", 0,
        Subsignal("tck", Pins(1)),
        Subsignal("tms", Pins(1)),
        Subsignal("tdi", Pins(1)),
        Subsignal("tdo", Pins(1)),
        Subsignal("trst", Pins(1)),
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
        # self.submodules.ticker_a = TickerZeroToMax(self.platform.request("ticker_zero_to_max"), max_cnt=15)
        # Ticker B
        # self.submodules.ticker_b = BeatTickerZeroToMax(self.platform.request("beat_ticker"), max_cnt_a=5, max_cnt_b=7)
        # JTAG Hello
        self.jtag_pads = jtag_pads = self.platform.request("jtag")
        # jtag_clk = self.platform.request("jtag_clk")
        # jtag_rst = self.platform.request("jtag_rst")
        # self.submodules.jtag_hello = JTAGHello(jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, jtag_pads.tdo,
        #           self.crg.cd_sys.rst, jtag_pads)
        # self.comb += jtag_pads.shift.eq(1) # what was this for
        # self.submodules.jev_tap = JTAGTAPFSM(jtag_pads.tms, jtag_pads.tck, ResetSignal("sys"))

        self.submodules.jev_tap = JTAGTAP(jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, jtag_pads.tdo, ResetSignal("sys"))

        self.specials.mohor_tap = MohorJTAGTAP(self.platform, jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, jtag_pads.tdo, jtag_pads.trst)

        self.specials.vcddumper = CocotbVCDDumperSpecial()

        if sim_debug:
            platform.add_debug(self, reset=1 if trace_reset_on else 0)
        else:
            self.comb += platform.trace.eq(1)


# Main ---------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteJTAG Simulation")
    parser.add_argument("--build", default=True,  action="store_true",     help="Build simulation")
    parser.add_argument("--run",   default=False,  action="store_true",     help="Run simulation")
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
        soc         = soc,
        build       = args.build,
        run         = args.run,
    )

@attr.s(auto_attribs=True)
class Sigs:
    clk: SimHandleBase
    rst: SimHandleBase
    tck: SimHandleBase
    tms: SimHandleBase
    tdi: SimHandleBase
    tdo: SimHandleBase
    trst: SimHandleBase

sigs = None

if cocotb.top is not None:
    clk = getattr(cocotb.top, srv.root.soc.crg.cd_sys.clk.name_override)
    rst = getattr(cocotb.top, srv.root.soc.crg.cd_sys.rst.name_override)
    tck = getattr(cocotb.top, srv.root.soc.jtag_pads.tck.name_override)
    tms = getattr(cocotb.top, srv.root.soc.jtag_pads.tms.name_override)
    tdi = getattr(cocotb.top, srv.root.soc.jtag_pads.tdi.name_override)
    tdo = getattr(cocotb.top, srv.root.soc.jtag_pads.tdo.name_override)
    trst = getattr(cocotb.top, srv.root.soc.jtag_pads.trst.name_override)
    sigs = Sigs(clk=clk, rst=rst,tck=tck, tms=tms, tdi=tdi, tdo=tdo, trst=trst)

    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())

async def tick_tms(dut, tms: int) -> None:
    # dut._log.info(f'tick_tms_internal {tms}')
    sigs.tms <= tms
    sigs.tck <= 0
    await tmr(clkper_ns / 2)
    sigs.tck <= 1
    await tmr(clkper_ns / 2)

tick_tms_ext = cocotb.function(tick_tms)


async def tick_tdi(dut, tdi: BitSequence) -> BitSequence:
    # dut._log.info(f'tick_tdi_bs_internal {tdi}')
    tdo = BitSequence()
    for di in tdi:
        sigs.tdi <= di
        sigs.tck <= 0
        await tmr(clkper_ns / 2)
        tdo += BitSequence(sigs.tdo.value.value, length=1)
        sigs.tck <= 1
        await tmr(clkper_ns / 2)
    return tdo

tick_tdi_ext = cocotb.function(tick_tdi)

async def tick_tdo(dut, nbits: int) -> BitSequence:
    # dut._log.info(f'tick_tdo {nbits}')
    tdi = BitSequence(0, length=nbits)
    tdo = await tick_tdi(dut, tdi)
    return tdo

tick_tdo_ext = cocotb.function(tick_tdo)


class SimJtagController(JtagController):
    def __init__(self, dut, trst: bool = False, frequency: float = 20e6):
        self.dut = dut
        self.trst = trst
        assert not trst
        self.freq = frequency
        self.p = dut._log.info
        self.p('SimJtagController __init__')

    def configure(self, url: str) -> None:
        raise NotImplementedError

    def close(self, freeze: bool = False) -> None:
        raise NotImplementedError

    def purge(self) -> None:
        raise NotImplementedError

    def reset(self, sync: bool = False) -> None:
        raise NotImplementedError

    def sync(self) -> None:
        raise NotImplementedError

    def write_tms(self, tms: BitSequence,
                  should_read: bool=False) -> None:
        self.p(f'write_tms(should_read={should_read}) with {tms}')
        for b in tms:
            tick_tms_ext(self.dut, b)

    def read(self, length: int) -> BitSequence:
        self.p(f'read({length})')
        tdo = tick_tdo_ext(self.dut, length)
        return tdo

    def write(self, out: Union[BitSequence, str], use_last: bool = True):
        self.p(f'write(use_last={use_last}) with {out}')
        tick_tdi_ext(self.dut, out)


    def write_with_read(self, out: BitSequence,
                        use_last: bool = False) -> int:
        raise NotImplementedError

    def read_from_buffer(self, length) -> BitSequence:
        raise NotImplementedError


async def reset_tap(dut):
    sigs.tck <= 0
    sigs.tms <= 0
    sigs.tdi <= 0
    sigs.tdo <= 1
    sigs.trst <= 0
    sigs.rst <= 0
    await tmr(clkper_ns)
    # sigs.trst <= 1
    sigs.rst <= 1
    await tmr(clkper_ns)
    sigs.trst <= 0
    sigs.rst <= 0
    await tmr(clkper_ns)


@cocotb.test()
async def read_idcode(dut):
    # dut = cocotb.top
    dut._log.info("Running read_idcode...")

    await reset_tap(dut)

    jte = JtagEngine()
    jte._ctrl = SimJtagController(dut)

    dut._log.info('shifting idcode instruction out')
    await ext(jte.write_ir)(IDCODE)
    # assert dut.update_ir.value == 1
    await tmr(clkper_ns)

    read_idcode = await ext(jte.read_dr)(32)
    # assert dut.update_dr.value == 1
    await tmr(clkper_ns)
    dut._log.info(f'read_idcode: {hex(int(read_idcode))} {read_idcode}')

    dut._log.info("Running read_idcode...done")



@cocotb.test()
async def reset_to_e1d(dut):
    # dut = cocotb.top
    dut._log.info("Running reset_to_e1d...")

    await reset_tap(dut)

    jte = JtagEngine()
    jte._ctrl = SimJtagController(dut)

    dut._log.info('going to exit_1_dr')
    await ext(jte.change_state)('exit_1_dr')
    # assert dut.exit1_dr.value == 1
    assert jte.state_machine.state() == jte.state_machine.states['exit_1_dr']
    await tmr(clkper_ns)

    dut._log.info('going to shift_ir')
    await ext(jte.change_state)('shift_ir')
    # assert dut.shift_ir.value == 1
    await tmr(clkper_ns)

    dut._log.info("Running reset_to_e1d...done")

if __name__ == "__main__":
    main()
