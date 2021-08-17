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
    wpn: SigType
    sio3: SigType

    @classmethod
    def from_pads(cls, pads: Record) -> QSPISigs:
        sig_dict = {p[0]: getattr(pads, p[0]) for p in pads.layout}
        return cls(**sig_dict)


CMD_READ: Final = 0x03
CMD_RDID: Final = 0x9f


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
        # self.rwpn_ts = rwpn_ts = TSTriple()
        # self.rsio3_ts = rsio3_ts = TSTriple()

        self.specials += rsi_ts.get_tristate(qrs.si)
        self.specials += rso_ts.get_tristate(qrs.so)
        # self.specials += rwpn_ts.get_tristate(qrs.wpn)
        # self.specials += rsio3_ts.get_tristate(qrs.sio3)


        self.esi_ts = esi_ts = TSTriple()
        self.eso_ts = eso_ts = TSTriple()
        # self.ewpn_ts = ewpn_ts = TSTriple()
        # self.esio3_ts = esio3_ts = TSTriple()

        self.specials += esi_ts.get_tristate(qes.si)
        self.specials += eso_ts.get_tristate(qes.so)
        # self.specials += ewpn_ts.get_tristate(qes.wpn)
        # self.specials += esio3_ts.get_tristate(qes.sio3)


        # self.comb += [
        #     qrs.sclk.eq(qes.sclk),
        #     qrs.rstn.eq(qes.rstn),
        #     qrs.csn.eq(qes.csn),
        #     qrs.si.eq(qes.si),
        #     qrs.so.eq(qes.so),
        #     qrs.wpn.eq(qes.wpn),
        #     qrs.sio3.eq(qes.sio3),
        # ]

        self.esi = esi = Signal()
        self.eso = eso = Signal()
        # self.ewpn = ewpn = Signal()
        # self.esio3 = esio3 = Signal()

        # self.comb += [
        #     esi.eq(esi_ts.i),
        #     eso.eq(rso_ts.i),
        # ]

        self.comb += [
            qrs.sclk.eq(qes.sclk),
            qrs.rstn.eq(qes.rstn),
            qrs.csn.eq(qes.csn),
            esi.eq(esi_ts.i),
            rsi_ts.o.eq(esi_ts.i),
            eso_ts.o.eq(rso_ts.i),
        ]

        self.comb += [
            esi_ts.oe.eq(0),
            eso_ts.oe.eq(1),
        ]

        self.comb += [
            rsi_ts.oe.eq(1),
            rso_ts.oe.eq(0),
        ]

        self.idcode = idcode = Signal(24, reset=0xc22539)

        # ctrl_fsm = FSM(reset_state='cmd')
        # ctrl_fsm = ClockDomainsRenamer('spi')(ctrl_fsm)
        # # ctrl_fsm = ResetInserter()(ctrl_fsm)
        # self.submodules.ctrl_fsm = ctrl_fsm
        #
        # ctrl_fsm.act('standby',
        #     NextState('cmd'),
        # )
        # ctrl_fsm.act('cmd',
        #     NextState('standby'),
        # )
        # ctrl_fsm.act('bad_cmd',
        #      NextState('fast_boot'),
        # )
        # ctrl_fsm.act('fast_boot',
        #     NextState('standby'),
        # )

        self.cmd_bit_cnt = cmd_bit_cnt = Signal(max=8)
        self.cmd = cmd = Signal(8)
        self.cmd_next = cmd_next = Signal(8)

        cmd_fsm = FSM(reset_state='get_cmd')
        cmd_fsm = ClockDomainsRenamer('spi')(cmd_fsm)
        # cmd_fsm = ResetInserter()(cmd_fsm)
        self.submodules.cmd_fsm = cmd_fsm

        self.get_cmd_flag = get_cmd_flag = Signal()
        cmd_fsm.act('get_cmd',
            get_cmd_flag.eq(cmd_bit_cnt == 7),
            cmd_next.eq(Cat(esi, cmd[:-1])),
            NextValue(cmd, cmd_next),
            NextValue(cmd_bit_cnt, cmd_bit_cnt + 1),
            If(cmd_bit_cnt == 7,
                If(cmd_next == CMD_READ,
                    NextState('read'),
                ).Elif(cmd_next == CMD_RDID,
                    NextState('rdid'),
                )
            ),
        )
        self.rdid_flag = rdid_flag = Signal()
        cmd_fsm.act('rdid',
            rdid_flag.eq(1),
            NextState('get_cmd'),
        )
        cmd_fsm.act('read',
            NextState('get_cmd'),
        )

        self.cnt = cnt = Signal(16)
        self.sync.spi += cnt.eq(cnt + 1)
