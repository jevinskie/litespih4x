# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer

from typing import Final

import attr
from bitstring import Bits

import cocotb

SigType = Signal
if cocotb.top is not None:
    SigObj = cocotb.handle.ModifiableObject

@attr.s(auto_attribs=True)
class QSPISigs:
    sclk: SigType
    rstn: SigType
    csn: SigType
    si: SigType
    so: SigType
    wp: SigType
    sio3: SigType

    @classmethod
    def from_pads(cls, pads: Record) -> QSPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)


class FlashEmu(Module):
    def __init__(self, qrs: QSPISigs, qes: QSPISigs):
        self.qrs = qrs
        self.qes = qes


        self.clock_domains.cd_spi = cd_spi = ClockDomain('spi')
        self.comb += ClockSignal('spi').eq(qes.sclk)
        self.comb += ResetSignal('spi').eq(~qes.rstn)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag, ResetSignal("sys"))

        self.rsi_ts = rsi_ts = TSTriple()
        self.rso_ts = rso_ts = TSTriple()
        self.rwp_ts = rwp_ts = TSTriple()
        self.rsio3_ts = rsio3_ts = TSTriple()

        self.specials += rsi_ts.get_tristate(qrs.si)
        self.specials += rso_ts.get_tristate(qrs.so)
        self.specials += rwp_ts.get_tristate(qrs.wp)
        self.specials += rsio3_ts.get_tristate(qrs.sio3)


        self.esi_ts = esi_ts = TSTriple()
        self.eso_ts = eso_ts = TSTriple()
        self.ewp_ts = ewp_ts = TSTriple()
        self.esio3_ts = esio3_ts = TSTriple()

        self.specials += esi_ts.get_tristate(qes.si)
        self.specials += eso_ts.get_tristate(qes.so)
        self.specials += ewp_ts.get_tristate(qes.wp)
        self.specials += esio3_ts.get_tristate(qes.sio3)


        self.comb += [
            qrs.sclk.eq(qes.sclk),
            qrs.rstn.eq(qes.rstn),
            qrs.csn.eq(qes.csn),
            qrs.si.eq(qes.si),
            qrs.so.eq(qes.so),
            qrs.wp.eq(qes.wp),
            qrs.sio3.eq(qes.sio3),
        ]

        self.comb += [
            esi_ts.oe.eq(0),
            eso_ts.oe.eq(1),
            ewp_ts.oe.eq(0),
            esio3_ts.oe.eq(0),
        ]


        self.submodules.ctrl_fsm = ctrl_fsm = ClockDomainsRenamer('spi')(FSM())
        self.idle = idle = Signal()
        self.twiddle = twiddle =Signal()
        ctrl_fsm.act('idle',
            idle.eq(1),
            NextState('twiddle'),
        )
        ctrl_fsm.act('twiddle',
            twiddle.eq(1),
            NextState('idle'),
        )

        self.cnt = cnt = Signal(16)
        self.sync.spi += cnt.eq(cnt + 1)
