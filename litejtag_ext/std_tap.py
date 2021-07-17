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


class StdTAPFSM(Module):
    def __init__(self, tms: Signal, trst: Signal):
        self.std_tck_cnt = std_tck_cnt = Signal(16)
        self.sync.jtag += std_tck_cnt.eq(std_tck_cnt + 1)

        self.NA = NA = Signal(1, reset=1)
        self.NB = NB = Signal(1, reset=1)
        self.NC = NC = Signal(1, reset=1)
        self.ND = ND = Signal(1, reset=1)

        self.state = state = Signal(4, reset_less=True)
        self.comb += state.eq(Cat(NA, NB, NC, ND))


class StdTAP(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):
        self.clock_domains.cd_jtag = cd_jtag = ClockDomain("jtag")
        self.comb += ClockSignal('jtag').eq(tck)
        self.comb += ResetSignal('jtag').eq(trst)
        # self.specials += AsyncResetSynchronizer(self.cd_jtag, ResetSignal("sys"))

        self.clock_domains.cd_jtag_inv = cd_jtag_inv = ClockDomain("jtag_inv")
        self.comb += ClockSignal("jtag_inv").eq(~tck)
        self.comb += ResetSignal('jtag_inv').eq(trst)

        self.submodules.state_fsm = fsm = StdTAPFSM(tms, tck)
