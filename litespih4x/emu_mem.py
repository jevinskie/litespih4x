# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
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
    def __init__(self, sz: int):
        self.sz = sz

        self.mem = self.specials.mem = mem = Memory(8, sz, init=[self.val4addr(a) for a in range(0x100)], name='flash_mem')
        self.rp = self.specials.rp = rp = mem.get_port(clock_domain='spi')
        self.rp_ext = self.specials.rp_ext = rp_ext = mem.get_port(clock_domain='sys')

        self.comb += rp.adr.eq(0)


    @staticmethod
    def val4addr(addr: int) -> int:
        return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)
