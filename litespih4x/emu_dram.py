from __future__ import annotations

from rich import print

from migen import *
from migen.genlib.cdc import AsyncClockMux
from migen.genlib.resetsync import AsyncResetSingleStageSynchronizer

from litex.soc.interconnect.csr import *

from litedram.core.crossbar import LiteDRAMNativePort, LiteDRAMNativeReadPort

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

        self.fill_addr = fill_addr = CSRStorage(port.address_width, reset_less=True, write_from_dev=True)
        self.fill_addr_storage = fill_addr.storage
        self.fa_tmp = fa_tmp = Signal.like(fill_addr.storage)
        self.readback_word = rb_word = CSRStorage(port.data_width, reset_less=True, write_from_dev=True)
        self.readback_word_storage = rb_word.storage
        self.rd_cnt = rd_cnt = CSRStorage(8, reset_less=True, write_from_dev=True)
        self.rd_cnt_storage = rd_cnt.storage
        self.rdc_tmp = rdc_tmp = Signal.like(rd_cnt.storage)
        self.go = go = CSRStorage(1, reset_less=True)
        self.go_sig = go_sig = go.storage

        self.combo_trigger = combo_trigger = Signal()
        self.comb += combo_trigger.eq(trigger | go_sig)

        self.submodules.ctrl_fsm = cfsm = ResetInserter()(FSM(name="ctrl_fsm"))
        self.comb += cfsm.reset.eq(~combo_trigger)
        self.idle_flag = idle_flag = Signal()
        self.rd_launch_flag = rd_launch_flag = Signal()
        self.rd_land_flag = rd_land_flag = Signal()
        self.reset_flag = reset_flag = Signal()

        cfsm.act("RESET",
            reset_flag.eq(1),
            If(combo_trigger,
                NextState("IDLE"),
            )
        )
        cfsm.delayed_enter("RESET", "IDLE", 16)
        cfsm.act("IDLE",
            idle_flag.eq(1),
            NextValue(rdc_tmp, rd_cnt.storage),
            NextValue(fa_tmp, fill_addr.storage),
            NextState("RD_LAUNCH"),
        )
        cfsm.delayed_enter("IDLE", "RD_LAUNCH", 16)

        cfsm.act("RD_LAUNCH",
            rd_launch_flag.eq(1),
            p.cmd.we.eq(0),
            p.cmd.addr.eq(fill_addr.storage),
            p.cmd.valid.eq(1),
            If(p.cmd.ready,
                rd_cnt.dat_w.eq(rd_cnt.storage - 1),
                rd_cnt.we.eq(1),
                fill_addr.dat_w.eq(fill_addr.storage + 1),
                fill_addr.we.eq(1),
                If(rd_cnt.storage == 0,
                    rd_cnt.dat_w.eq(rdc_tmp),
                    rd_cnt.we.eq(1),
                    NextState("RD_LAND"),
                )
            ),
        )
        cfsm.act("RD_LAND",
            rd_land_flag.eq(1),
            p.rdata.ready.eq(1),
            If(p.rdata.valid,
                rb_word.dat_w.eq(p.rdata.data),
                rb_word.we.eq(1),
                rd_cnt.dat_w.eq(rd_cnt.storage - 1),
                rd_cnt.we.eq(1),
                If(rd_cnt.storage == 0,
                    rd_cnt.dat_w.eq(rdc_tmp),
                    rd_cnt.we.eq(1),
                    fill_addr.dat_w.eq(fa_tmp),
                    fill_addr.we.eq(1),
                    NextState("RESET"),
                )
            ),
        )

class FlashEmuDRAMLite(Module):
    def __init__(self, port: LiteDRAMNativeReadPort, prefetch_bits: int, paddr: Signal, paddr_valid: Signal):
        self.port = p = port

        self.read_addr = read_addr = Signal(port.address_width)

        prefetch_byte_sz = 2**prefetch_bits
        prefetch_bit_sz = prefetch_byte_sz * 8
        num_prefetch_reads = prefetch_bit_sz // port.data_width
        self.prefetch_regs = pf_regs = Array(Signal(port.data_width, name=f'pf_r{i}') for i in range(num_prefetch_reads))
        self.rd_cnt = rd_cnt = Signal(max=num_prefetch_reads, reset=num_prefetch_reads)

        self.submodules.ctrl_fsm = cfsm = FSM(name="dram_fsm", reset_state="IDLE")
        self.idle_flag = idle_flag = Signal()
        self.rd_launch_flag = rd_launch_flag = Signal()
        self.rd_land_flag = rd_land_flag = Signal()

        self.paddr_tmp = paddr_tmp = Signal.like(paddr)

        cfsm.act("IDLE",
            idle_flag.eq(1),
            NextValue(rd_cnt, rd_cnt.reset),
            If(paddr_valid,
               NextValue(paddr_tmp, paddr),
               NextValue(read_addr, paddr[4:]),
               NextState("RD_LAUNCH"),
            ),
        )
        cfsm.act("RD_LAUNCH",
            rd_launch_flag.eq(1),
            p.cmd.we.eq(0),
            p.cmd.addr.eq(read_addr),
            p.cmd.valid.eq(1),
            If(p.cmd.ready,
                NextValue(rd_cnt, rd_cnt - 1),
                NextValue(read_addr, read_addr + 1),
                If(rd_cnt == 0,
                    NextValue(rd_cnt, rd_cnt.reset),
                    NextState("RD_LAND"),
                )
            ),
        )
        cfsm.act("RD_LAND",
            rd_land_flag.eq(1),
            p.rdata.ready.eq(1),
            If(p.rdata.valid,
                NextValue(pf_regs[num_prefetch_reads - rd_cnt], p.rdata.data),
                NextValue(rd_cnt, rd_cnt - 1),
                If(rd_cnt == 0,
                    NextState("IDLE"),
                ),
            ),
        )