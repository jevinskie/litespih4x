# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncClockMux
from migen.genlib.resetsync import AsyncResetSingleStageSynchronizer

from litex.soc.interconnect.csr import *

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

class FakeMemoryPort:
    def __init__(self, adr: Signal, dat_r: Signal, dat_w: Optional[Signal] = None, we: Optional[Signal] = None):
        self.adr = adr
        self.dat_r = dat_r
        if dat_w is not None:
            assert we is not None
            self.dat_w = dat_w
            self.we = we

class MemoryPortMux(Module):
    def __init__(self, real_port, sel: Signal):
        self.p = p = real_port
        write_capable = getattr(p, 'we', None) is not None

        p0_adr = Signal(p.adr.nbits)
        p0_dat_r = Signal(p.dat_w.nbits)
        p1_adr = Signal(p.adr.nbits)
        p1_dat_r = Signal(p.dat_w.nbits)

        self.comb += [
            p0_dat_r.eq(p.dat_r),
            p1_dat_r.eq(p.dat_r),
            If(~sel,
                p.adr.eq(p0_adr),
            ).Else(
                p.adr.eq(p1_adr),
            ),
        ]

        if not write_capable:
            p0_dat_w = p0_we = p1_dat_w = p1_we = None
        else:
            p0_dat_w = Signal(p.dat_w.nbits)
            p0_we = Signal()
            p1_dat_w = Signal(p.dat_w.nbits)
            p1_we = Signal()

            self.comb += [
                If(~sel,
                    p.dat_w.eq(p0_dat_w),
                    p.we.eq(p0_we),
                ).Else(
                    p.dat_w.eq(p1_dat_w),
                    p.we.eq(p1_we),
                )
            ]

        self.p0 = FakeMemoryPort(adr=p0_adr, dat_r=p0_dat_r, dat_w=p0_dat_w, we=p0_we)
        self.p1 = FakeMemoryPort(adr=p1_adr, dat_r=p1_dat_r, dat_w=p1_dat_w, we=p1_we)


class FlashEmuMem(Module):
    def __init__(self, cd_sys: ClockDomain, cd_spi: ClockDomain, sz: int):
        self.sz = sz

        self.sel_csr = sel_csr = CSRStorage(fields=[
            CSRField("sel", size=1, offset=0, reset=1,
                     description="""Selects the memory interface for use by the SoC, not the SPI controller"""),
        ])
        self.sel = sel = sel_csr.fields.sel

        self.clock_domains.cd_spimem = cd_spimem = ClockDomain('spimem')
        self.specials.clk_mux = clk_mux = AsyncClockMux(cd_sys, cd_spi, cd_spimem, sel, cd_sys.rst)

        self.mem = self.specials.mem = mem = Memory(8, sz, init=[self.val4addr(a) for a in range(sz)], name='flash_mem')
        self.specials.real_port = real_port = mem.get_port(clock_domain='spimem', write_capable=True)

        self.mpm = self.submodules.mem_port_mux = mpm = MemoryPortMux(real_port, sel)
        self.loader_port = mpm.p0
        self.spiemu_port = mpm.p1

    @staticmethod
    def val4addr(addr: int) -> int:
        return (addr & 0xff) ^ ((addr >> 8) & 0xff) ^ ((addr >> 16) & 0xff) ^ ((addr >> 24) & 0xff)

    def get_memories(self):
        return [(False, self.mem, self.loader_port)]

    def get_csrs(self):
        return [self.sel_csr, ]
