# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncClockMux
from migen.genlib.resetsync import AsyncResetSingleStageSynchronizer

from typing import Final, Optional, Union

import attr

import cocotb

SigType = Signal
if cocotb.top is not None:
    SigType = cocotb.handle.ModifiableObject


@attr.s(auto_attribs=True)
class QSPIMemSigs:
    sclk: SigType

    @classmethod
    def from_pads(cls, pads: Record) -> QSPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)


class FlashEmuMem(Module):
    def __init__(self, cd_sys: ClockDomain, cd_spi: ClockDomain, sz: int):
        self.sz = sz

        self.clock_domains.cd_spimem = cd_spimem = ClockDomain('spimem')
        self.clk_sel = clk_sel = Signal(reset=1)
        self.specials.clk_mux = clk_mux = AsyncClockMux(cd_sys, cd_spi, cd_spimem, clk_sel, cd_sys.rst)


        self.mem = self.specials.mem = mem = Memory(8, sz, init=[self.val4addr(a) for a in range(sz)], name='flash_mem')
        self.rp = self.specials.rp = rp = mem.get_port(clock_domain='spimem')

        # self.comb += rp.adr.eq(0)


    @staticmethod
    def val4addr(addr: int) -> int:
        return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)
