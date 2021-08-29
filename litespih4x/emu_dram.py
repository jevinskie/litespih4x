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


class FlashEmuDRAM(Module):
    def __init__(self, port: LiteDRAMNativePort, trigger: Signal):
        self.port = p = port
        self.trigger = t = trigger

        self.submodules.ctrl_fsm = cfsm = ResetInserter()(FSM())
        self.comb += cfsm.reset.eq(~trigger)
        self.idle_flag = idle_flag = Signal()
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
        cfsm.delayed_enter("IDLE", "RD_LAUNCH", 16)
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
