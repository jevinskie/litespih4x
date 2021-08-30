from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncClockMux
from migen.genlib.resetsync import AsyncResetSingleStageSynchronizer

from litex.soc.interconnect.csr import *

from litedram.core.crossbar import LiteDRAMNativePort

from typing import Final, Optional, Union

import attr

import cocotb

SigType = Signal
if cocotb.top is not None:
    SigType = cocotb.handle.ModifiableObject


class FlashEmuDRAM(Module, AutoCSR):
    def __init__(self, port: LiteDRAMNativePort, trigger: Signal):
        self.port = p = port
        self.trigger = t = trigger

        self.fill_word = fill_word = CSRStorage(32, reset=0xDEADBEEF)
        self.fill_word_storage = fw_storage = fill_word.storage

        self.submodules.ctrl_fsm = cfsm = ResetInserter()(FSM())
        self.comb += cfsm.reset.eq(~trigger)
        self.idle_flag = idle_flag = Signal()
        self.wr_launch_flag = wr_launch_flag = Signal()
        self.wr_land_flag = wr_land_flag = Signal()
        self.rd_launch_flag = rd_launch_flag = Signal()
        self.rd_land_flag = rd_land_flag = Signal()
        self.reset_flag = reset_flag = Signal()

        self.comb += p.rdata.ready.eq(1)

        cfsm.act("RESET",
            reset_flag.eq(1),
            If(trigger,
                NextState("IDLE"),
            )
        )
        cfsm.delayed_enter("RESET", "IDLE", 16)
        cfsm.act("IDLE",
            idle_flag.eq(1),
            NextState("RD_LAUNCH"),
        )
        cfsm.delayed_enter("IDLE", "WR_LAUNCH", 16)

        cfsm.act("WR_LAUNCH",
            wr_launch_flag.eq(1),
            p.cmd.we.eq(1),
            p.cmd.addr.eq(0xaaa0),
            p.wdata.data.eq(0xDEADBEEF),
            p.wdata.we.eq(0xF),
            p.cmd.valid.eq(1),
            p.wdata.valid.eq(1),
            If(p.cmd.ready & p.wdata.ready,
                NextState("RD_LAUNCH"),
            )
        )
        # cfsm.act("WR_LAND",
        #     wr_land_flag.eq(1),
        #     p.rdata.ready.eq(1),
        #     If(p.rdata.valid,
        #         NextState("RD_LAUNCH"),
        #     ),
        # )

        cfsm.delayed_enter("WR_LAUNCH", "RD_LAUNCH", 64)


        cfsm.act("RD_LAUNCH",
            rd_launch_flag.eq(1),
            p.cmd.we.eq(0),
            p.cmd.addr.eq(0xaaa0),
            p.cmd.valid.eq(1),
            If(p.cmd.ready,
                NextState("RD_LAND"),
            )
        )
        cfsm.act("RD_LAND",
            rd_land_flag.eq(1),
            p.rdata.ready.eq(1),
            If(p.rdata.valid,
                NextState("IDLE"),
            ),
        )
