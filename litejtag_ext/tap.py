# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

# portions from https://github.com/ChrisPVille/jtaglet
#
# Copyright 2018 Christopher Parish
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from litex.soc.cores.jtag import JTAGTAPFSM

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer

from typing import Final
from bitstring import Bits

# OP_IDCODE: Final = Constant(0b00_0000_0110, 10)
OP_IDCODE: Final = Constant(0b0010, 4)
# OP_IDCODE: Final = Constant(0b0_0010, 5)
# OP_USER0: Final = Constant(0xc, 10)
# OP_USER1: Final = Constant(0xe, 10)
# OP_BYPASS: Final = Constant(0b11_1111_1111, 10)
# OP_BYPASS: Final = Constant(0b1_1111, 5)
OP_BYPASS: Final = Constant(0b1111, 4)
IDCODE: Final = Constant(0x0310_50DD, 32)

class BYPASSReg(Module):
    def __init__(self, tdi: Signal, tdo: Signal, tap_fsm: JTAGTAPFSM):
        self.dr = dr = Signal(1, reset=1)

        self.comb += [
            If(tap_fsm.TEST_LOGIC_RESET | tap_fsm.CAPTURE_DR,
                dr.eq(dr.reset),
            ).Elif(tap_fsm.SHIFT_DR,
                tdo.eq(dr),
            ),
        ]

        self.sync.jtag += [
            If(tap_fsm.SHIFT_DR,
                dr.eq(tdi),
            )
        ]


class IDCODEReg(Module):
    def __init__(self, tdi: Signal, tdo: Signal, idcode: Constant, tap_fsm: JTAGTAPFSM):
        self.dr = dr = Signal(32, reset=idcode.value)

        self.comb += [
            If(tap_fsm.TEST_LOGIC_RESET | tap_fsm.CAPTURE_DR,
                dr.eq(dr.reset),
            ).Elif(tap_fsm.SHIFT_DR,
                tdo.eq(dr),
            ),
        ]

        self.sync.jtag += [
            If(tap_fsm.SHIFT_DR,
                dr.eq(Cat(dr[1:], tdi)),
            )
        ]

class JTAGTAP(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, sys_rst: Signal):
        self.clock_domains.cd_jtag = cd_jtag = ClockDomain("jtag")
        self.comb += ClockSignal('jtag').eq(tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag, ResetSignal("sys"))

        self.clock_domains.cd_jtag_inv = cd_jtag_inv = ClockDomain("jtag_inv")
        self.comb += ClockSignal("jtag_inv").eq(~tck)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag_inv, ResetSignal("sys"))

        self.submodules.state_fsm = fsm = JTAGTAPFSM(tms, tck)

        self.idcode_tdo = idcode_tdo = Signal()
        self.submodules.idcode = ClockDomainsRenamer("jtag")(
            IDCODEReg(tdi, idcode_tdo, idcode=IDCODE, tap_fsm=self.state_fsm)
        )

        self.bypass_tdo = bypass_tdo = Signal()
        self.submodules.bypass = ClockDomainsRenamer("jtag")(
            BYPASSReg(tdi, bypass_tdo, tap_fsm=self.state_fsm)
        )

        self.ir = ir = Signal(OP_IDCODE.nbits, reset=OP_IDCODE)
        self.ir_tdo = ir_tdo = Signal()
        self.comb += ir_tdo.eq(ir[0])

        self.sync.jtag += [
            If(fsm.TEST_LOGIC_RESET,
                ir.eq(ir.reset)
            ).Elif(fsm.CAPTURE_IR,
                ir.eq(1)
            ).Elif(fsm.SHIFT_IR,
                ir.eq(Cat(ir[1:], tdi))
            )
        ]

        self.tdo_pre = tdo_pre = Signal()
        self.comb += [
            If(fsm.SHIFT_DR,
                Case(ir, {
                    OP_IDCODE: tdo_pre.eq(idcode_tdo),
                    OP_BYPASS: tdo_pre.eq(bypass_tdo),
                    'default': tdo_pre.eq(bypass_tdo),
                })
            ).Elif(fsm.SHIFT_IR,
                tdo_pre.eq(ir_tdo),
            )
        ]

        self.sync.jtag_inv += [
            tdo.eq(tdo_pre),
        ]

        # self.submodules.tap_fsm = FSM(clock_domain=cd_jtag.name)

