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

        # self.fill_word = fill_word = CSRStorage(32, reset=0xDEADBEEF)
        # self.fill_word_storage = fw_storage = fill_word.storage
        self.fill_addr = fill_addr = CSRStorage(32, reset_less=True)
        self.fill_addr_storage = fa_storage = fill_addr.storage
        self.readback_word = rb_word = CSRStorage(32, reset_less=True)
        self.readback_word_storage = rbw_storage = rb_word.storage
        self.rd_cnt = rd_cnt = CSRStorage(8, reset_less=True)
        self.rd_cnt_storage = rdc_storage = rd_cnt.storage
        self.rdc_tmp = rdc_tmp = Signal.like(rdc_storage)
        self.go = go = CSRStorage(1, reset_less=True)
        self.go_sig = go_sig = go.storage

        self.combo_trigger = combo_trigger = Signal()
        self.comb += combo_trigger.eq(trigger | go_sig)

        # self.submodules.ctrl_fsm = cfsm = FSM()
        self.submodules.ctrl_fsm = cfsm = ResetInserter()(FSM(name="ctrl_fsm"))
        self.comb += cfsm.reset.eq(~trigger)
        self.idle_flag = idle_flag = Signal()
        self.wr_launch_flag = wr_launch_flag = Signal()
        self.wr_land_flag = wr_land_flag = Signal()
        self.rd_launch_flag = rd_launch_flag = Signal()
        self.rd_land_flag = rd_land_flag = Signal()
        self.reset_flag = reset_flag = Signal()

        cfsm.act("RESET",
            reset_flag.eq(1),
            If(trigger,
                NextState("IDLE"),
            )
        )
        cfsm.delayed_enter("RESET", "IDLE", 16)
        cfsm.act("IDLE",
            idle_flag.eq(1),
            NextValue(rdc_tmp, rdc_storage),
            NextState("RD_LAUNCH"),
        )
        cfsm.delayed_enter("IDLE", "RD_LAUNCH", 16)

        # cfsm.act("WR_LAUNCH",
        #     wr_launch_flag.eq(1),
        #     p.cmd.we.eq(1),
        #     p.cmd.addr.eq(fa_storage),
        #     p.wdata.data.eq(fw_storage),
        #     p.wdata.we.eq(0xF),
        #     p.cmd.valid.eq(1),
        #     p.wdata.valid.eq(1),
        #     If(p.cmd.ready & p.wdata.ready,
        #         NextState("RD_LAUNCH"),
        #     )
        # )
        # cfsm.act("WR_LAND",
        #     wr_land_flag.eq(1),
        #     p.rdata.ready.eq(1),
        #     If(p.rdata.valid,
        #         NextState("RD_LAUNCH"),
        #     ),
        # )

        # cfsm.delayed_enter("WR_LAUNCH", "RD_LAUNCH", 64)
        cfsm.act("RD_LAUNCH",
            rd_launch_flag.eq(1),
            p.cmd.we.eq(0),
            p.cmd.addr.eq(fa_storage),
            p.cmd.valid.eq(1),
            If(p.cmd.ready,
                NextValue(rdc_storage, rdc_storage - 1),
                NextValue(fa_storage, fa_storage + 1),
                If(rdc_storage == 0,
                    NextValue(rdc_storage, rdc_tmp),
                    NextState("RD_LAND"),
                )
            ),
        )
        cfsm.act("RD_LAND",
            rd_land_flag.eq(1),
            p.rdata.ready.eq(1),
            If(p.rdata.valid,
                NextValue(rbw_storage, p.rdata.data),
                NextValue(rdc_storage, rdc_storage - 1),
                If(rdc_storage == 0,
                    NextState("RESET"),
                )
            ),
        )
        # cfsm.delayed_enter("RD_LAND", "RESET", 64)


        # cfsm.act("RD_LAUNCH",
        #     rd_launch_flag.eq(1),
        #     p.cmd.we.eq(0),
        #     p.cmd.addr.eq(fa_storage),
        #     p.cmd.valid.eq(1),
        #     If(rdc_storage == 0,
        #         If(p.cmd.ready,
        #             NextState("RD_LAND"),
        #         ),
        #     ).Else(
        #         NextValue(rdc_storage, rdc_storage - 1),
        #         NextValue(fa_storage, fa_storage + 1)
        #     ),
        # )
        # cfsm.act("RD_LAND",
        #     rd_land_flag.eq(1),
        #     p.rdata.ready.eq(1),
        #     If(p.rdata.valid,
        #         NextValue(rbw_storage, p.rdata.data),
        #         NextState("RESET"),
        #     ),
        # )
