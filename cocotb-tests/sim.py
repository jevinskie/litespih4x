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

from litejtag_ext.hello import TickerZeroToMax, BeatTickerZeroToMax, JTAGHello
from litejtag_ext.mohor_tap import MohorJTAGTAP
from litejtag_ext.jtaglet_tap import JtagletJTAGTAP
from litejtag_ext.tap import JTAGTAP
from litejtag_ext.std_tap import StdTAP

import cocotb
from cocotb.triggers import Timer, ReadWrite, ReadOnly, NextTimeStep
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ModifiableObject

from pyftdi.jtag import *

import attr
from rich import inspect as rinspect

srv: Final = start_sim_server()
ext: Final = cocotb.external

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

        self.std_tdo = std_tdo = Signal()
        self.submodules.std_tap = StdTAP(jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, std_tdo, jtag_pads.trst)

        foo = self.jev_tap.state_fsm.TEST_LOGIC_RESET
        print(foo)

        if dump:
            with open('jev_tap.v', 'w') as f:
                f.write(str(verilog.convert(self.jev_tap)))
            with open('std_tap.v', 'w') as f:
                f.write(str(verilog.convert(self.std_tap)))
            sys.exit(0)

        self.mohor_tdo = mohor_tdo = Signal()
        self.specials.mohor_tap = MohorJTAGTAP(self.platform, jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, mohor_tdo, jtag_pads.trst)

        self.jtaglet_tdo = jtaglet_tdo = Signal()
        self.specials.jtaglet_tap = JtagletJTAGTAP(self.platform, jtag_pads.tms, jtag_pads.tck, jtag_pads.tdi, jtaglet_tdo, jtag_pads.trst)

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
    tck: ModifiableObject
    tms: ModifiableObject
    tdi: ModifiableObject
    tdo: ModifiableObject
    trst: ModifiableObject
    TLR: ModifiableObject


sigs = None
soc = None
ns = None

def nol(sig: Signal) -> str:
    return sig.name_override

def nsl(sig: Signal) -> str:
    return ns.pnd[sig]

if cocotb.top is not None:
    soc = srv.root.soc
    ns = srv.root.ns
    j = soc.jtag_pads
    t = cocotb.top
    jf = soc.jev_tap.state_fsm

    d = {}
    # FIXME: why doesnt nsl work for CRG signals?
    d['clk']  = getattr(t, nol(soc.crg.cd_sys.clk))
    d['rst']  = getattr(t, nol(soc.crg.cd_sys.rst))
    d['tck']  = getattr(t, nsl(j.tck))
    d['tms']  = getattr(t, nsl(j.tms))
    d['tdi']  = getattr(t, nsl(j.tdi))
    d['tdo']  = getattr(t, nsl(j.tdo))
    d['trst'] = getattr(t, nsl(j.trst))
    d['TLR']  = getattr(t, nsl(jf.TEST_LOGIC_RESET))

    sigs = Sigs(**d)

def xbits(n, hi, lo):
    return (n >> lo) & (2**(hi+1 - lo) - 1)

def fork_clk():
    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())

async def tick_tms(dut, tms: int) -> None:
    dut._log.info(f'tick_tms_internal tms: {tms} tck: {sigs.tck.value}')
    sigs.tms <= tms
    await ReadOnly()
    assert sigs.tck.value == 0
    await tclkh
    sigs.tck <= 1
    await tclkh
    sigs.tck <= 0

tick_tms_ext = cocotb.function(tick_tms)


async def tick_tdi(dut, tdi: BitSequence) -> BitSequence:
    dut._log.info(f'tick_tdi_bs_internal {tdi} {int(tdi)} tck: {sigs.tck.value}')
    tdo = BitSequence()
    for di in tdi:
        dut._log.info(f'tick_tdi_bs_internal bit {di}')
        sigs.tdi <= di
        await ReadOnly()
        assert sigs.tck.value == 0
        await tclkh
        sigs.tck <= 1
        tdo += BitSequence(sigs.tdo.value.value, length=1)
        await tclkh
        sigs.tck <= 0
    await NextTimeStep()
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


@cocotb.test()
async def reset_tap(dut):
    fork_clk()
    sigs.tck <= 0
    sigs.tms <= 0
    sigs.tdi <= 0
    sigs.tdo <= 1
    sigs.trst <= 0
    sigs.rst <= 0
    await tclk
    sigs.trst <= 1
    sigs.rst <= 1
    await tclk
    sigs.trst <= 0
    sigs.rst <= 0
    await tclk
    print(f'at end of reset tck: {sigs.tck.value}')

@cocotb.test(skip=True)
async def openocd_srv(dut):
    fork_clk()
    p = dut._log.info
    p("Running openocd_srv...")
    await tmr(2*clkper_ns)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 2430))
    s.listen(1)
    conn, addr = s.accept()
    p(f'connected by {addr} conn: {conn}')
    while True:
        cmd = conn.recv(1)
        if cmd is None:
            break
        if cmd == b'B':
            p('BLINK ON')
        elif cmd == b'b':
            p('BLINK OFF')
        elif cmd == b'R':
            conn.sendall(bytes([ord(str(sigs.tdo.value))]))
        elif cmd == b'Q':
            p('QUIT req')
            s.close()
            break
        elif b'0' <= cmd <= b'7':
            v = int(cmd.decode('utf-8'))
            sigs.tck <= (v & 2**2) >> 2
            sigs.tms <= (v & 2**1) >> 1
            sigs.tdi <= (v & 2**0) >> 0
            await tclkh
        elif cmd == b'r' or cmd == b's':
            sigs.trst <= 0
            await tclk
        elif cmd == b't' or cmd == b'u':
            sigs.trst <= 1
            await tclk
        else:
            raise ValueError

    await tmr(4*clkper_ns)
    p("Running openocd_srv...done")



@cocotb.test(skip=False)
async def read_idcode(dut):
    fork_clk()
    dut._log.info("Running read_idcode...")
    await tmr(2*clkper_ns)

    jte = JtagEngine()
    jte._ctrl = SimJtagController(dut)

    # await ext(jte.change_state)('capture_ir')
    # assert dut.CAPTURE_IR.value == 1
    # dut._log.info('in capture-ir')

    # await tmr(2*clkper_ns)


    dut._log.info('shifting idcode instruction out')
    await ext(jte.write_ir)(IDCODE)
    await tmr(clkper_ns)

    await tmr(2*clkper_ns)

    await tmr(2*clkper_ns)

    dut._log.info('changing state after write_ir')
    await ext(jte.change_state)('test_logic_reset')
    assert sigs.TLR.value == 1
    await tmr(2 * clkper_ns)

    read_idcode = await ext(jte.read_dr)(32)
    # assert dut.update_dr.value == 1
    await tmr(clkper_ns)
    dut._log.info(f'read_idcode: {hex(int(read_idcode))} {read_idcode}')



    await tmr(4*clkper_ns)
    dut._log.info("Running read_idcode...done")



@cocotb.test(skip=True)
async def reset_to_e1d(dut):
    fork_clk()
    dut._log.info("Running reset_to_e1d...")
    await tmr(2*clkper_ns)

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
