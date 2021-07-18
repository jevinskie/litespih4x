# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer

class TickerZeroToMax(Module):
    def __init__(self, pads: Record, max_cnt: int):
        self.counter = counter = Signal(max=max_cnt)
        self.tick = tick = Signal()
        assert counter.nbits <= pads.counter.nbits

        self.comb += pads.tick.eq(tick)
        self.comb += pads.counter.eq(counter)
        self.sync += \
            If(counter == max_cnt,
               tick.eq(1),
               counter.eq(0)
            ).Else(
                tick.eq(0),
                counter.eq(counter + 1)
            )

    @classmethod
    def from_period(cls, pads: Record, sys_clk_freq: int, ticker_period: float) -> TickerZeroToMax:
        counter_preload = int(sys_clk_freq * ticker_period) - 1
        return cls(pads, counter_preload)

    @classmethod
    def from_freq(cls, pads: Record, sys_clk_freq: int, ticker_freq: int) -> TickerZeroToMax:
        return cls.from_period(pads, sys_clk_freq, 1 / ticker_freq)


class BeatTickerZeroToMax(Module):
    def __init__(self, pads: Record, max_cnt_a: int, max_cnt_b: int):
        self.tick = tick = Signal()

        pads_a = Record([
            ("tick", pads.tick_a),
            ("counter", pads.counter_a),
        ], "ticker_a")
        self.submodules.ticker_a = TickerZeroToMax(pads_a, max_cnt_a)

        pads_b = Record([
            ("tick", pads.tick_b),
            ("counter", pads.counter_b),
        ], "ticker_b")
        self.submodules.ticker_b = TickerZeroToMax(pads_b, max_cnt_b)

        self.comb += pads.tick.eq(tick)
        self.comb += tick.eq(self.ticker_a.tick & self.ticker_b.tick)

    @classmethod
    def from_period(cls, pads: Record, sys_clk_freq: int, ticker_period_a: float, ticker_period_b: float) -> BeatTickerZeroToMax:
        counter_preload_a = int(sys_clk_freq * ticker_period_a) - 1
        counter_preload_b = int(sys_clk_freq * ticker_period_b) - 1
        return cls(pads, max_cnt_a=counter_preload_a, max_cnt_b=counter_preload_b)

    @classmethod
    def from_freq(cls, pads: Record, sys_clk_freq: int, ticker_freq_a: int, ticker_freq_b: int) -> BeatTickerZeroToMax:
        return cls.from_period(pads, sys_clk_freq, 1 / ticker_freq_a, 1 / ticker_freq_b)



# class HelloReg(Module):
#     def __init__(self, tdi: Signal, tdo: Signal, hellocode: Constant, tap_fsm: JTAGTAPFSM):
#         self.dr = dr = Signal(32, reset=hellocode.value)
#
#         self.comb += [
#             If(tap_fsm.TEST_LOGIC_RESET | tap_fsm.CAPTURE_DR,
#                 dr.eq(dr.reset),
#             ).Elif(tap_fsm.SHIFT_DR,
#                 tdo.eq(dr),
#             ),
#         ]
#
#         self.sync.jtag += [
#             If(tap_fsm.SHIFT_DR,
#                 dr.eq(Cat(dr[1:], tdi)),
#             )
#         ]


class JTAGHello(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, rst: Signal, phy: Module):
        self.hello_dr = hello_dr = Signal(32, reset=0xAA00FF55)

        self.comb += tdo.eq(hello_dr[0])

        self.sync.jtag += [
            If(phy.shift,
                hello_dr.eq(Cat(hello_dr[1:], tdi)),
            ),
        ]

        # # #
