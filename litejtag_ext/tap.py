# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from litex.soc.cores.jtag import JTAGTAPFSM

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer


class JTAGTAP(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, sys_rst: Signal):
        self.clock_domains.cd_jtag = cd_jtag = ClockDomain("jtag")
        self.comb += ClockSignal('jtag').eq(tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag, ResetSignal("sys"))

        self.clock_domains.cd_jtag_inv = cd_jtag_inv = ClockDomain("jtag_inv")
        self.comb += ClockSignal("jtag_inv").eq(~tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag_inv, ResetSignal("sys"))

        self.submodules.state_fsm = JTAGTAPFSM(tms, tck, sys_rst)

        # self.submodules.tap_fsm = FSM(clock_domain=cd_jtag.name)

