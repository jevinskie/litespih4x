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

        self.submodules.ctrl_fsm = cfsm = FSM()
        self.idle_flag = idle_flag = Signal()
        self.cmd_rd_flag = cmd_rd_flag = Signal()

        cfsm.act("IDLE",
            idle_flag.eq(1),
            If(trigger,
                NextState("RD"),
            )
        )
        cfsm.delayed_enter("IDLE", "RD", 4)
        cfsm.act("RD",
            cmd_rd_flag.eq(1),
            p.cmd.we.eq(0),
            p.cmd.addr.eq(0xaaa0),
            p.cmd.valid.eq(1),
            NextState("IDLE"),
        )

    def do_finalize(self):
        super().do_finalize()
