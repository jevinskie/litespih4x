# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *

class TickerZeroToMax(Module):
    def __init__(self, pads: Record, max_cnt: int):
        self.counter = counter = Signal(max=max_cnt)
        self.tick = tick = Signal()
        print(pads)
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


class JTAGHello(Module):
    def __init__(self, jtag_clk: Signal, jtag_rst: Signal, pads: Record):
        self.clock_domains.cd_jtag = ClockDomain()

        self.hello_code = sr = Signal(32, reset=int.from_bytes(b'HELO', byteorder='little', signed=False))
        self.buf = buf = Signal()

        self.comb += [
            ClockSignal('jtag').eq(pads.tck),
            ResetSignal('jtag').eq(pads.reset),
            # self.cd_jtag.clk.eq(ClockSignal('jtag')),
            pads.tck.eq(jtag_clk),
            pads.reset.eq(jtag_rst),
            # pads.tdo.eq(sr[31]),
            pads.tdo.eq(buf),
        ]
        self.sync.jtag += [
            # sr.eq(Cat(sr[1:], pads.tdi)),
            buf.eq(~pads.tdi),
        ]

        # # #
