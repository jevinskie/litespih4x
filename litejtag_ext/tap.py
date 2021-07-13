# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from litex.soc.cores.jtag import JTAGTAPFSM

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer

from bitstring import Bits

class IDCODE(Module):
    def __init__(self, tck: Signal, idcode_opcode: Bits, idcode: Bits, tap_fsm: JTAGTAPFSM):
        self.tdoz = tdoz = Signal()
        self.dr = dr = Signal(32, reset=0x149511c3)
        self.dr_reg = dr_reg = Signal()
        self.clock_domains.cd_jtag_inv = cd_jtag_inv = ClockDomain("jtag_inv")
        self.comb += ClockSignal("jtag_inv").eq(~tck)

        self.comb += [
            If(tap_fsm.TEST_LOGIC_RESET | tap_fsm.CAPTURE_DR,
                dr.eq(dr.reset),
            ),
        ]

        self.sync += [
            If(tap_fsm.SHIFT_DR,
                dr.eq(Cat(dr[1:], 0)),
            )
        ]

        self.sync.jtag_inv += [
            If(tap_fsm.SHIFT_DR,
               tdoz.eq(dr[0]),
           ),
        ]

class JTAGTAP(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, sys_rst: Signal):
        self.clock_domains.cd_jtag = cd_jtag = ClockDomain("jtag")
        self.comb += ClockSignal('jtag').eq(tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag, ResetSignal("sys"))

        self.clock_domains.cd_jtag_inv = cd_jtag_inv = ClockDomain("jtag_inv")
        self.comb += ClockSignal("jtag_inv").eq(~tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag_inv, ResetSignal("sys"))

        self.submodules.state_fsm = JTAGTAPFSM(tms, tck)
        self.submodules.idcode = ClockDomainsRenamer("jtag")(IDCODE(tck, Bits('0b0010'), Bits('0x149511c3'), self.state_fsm))

        # self.submodules.tap_fsm = FSM(clock_domain=cd_jtag.name)

