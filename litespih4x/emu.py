# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from rich import print

from migen import *
from migen.genlib.cdc import AsyncResetSynchronizer

from typing import Final
from bitstring import Bits


class FlashEmu(Module):
    def __init__(self, csn: Signal,
                 si: TSTriple, so: TSTriple, wp: TSTriple, sio3: TSTriple):

        self.submodules.ctrl_fsm = ctrl_fsm = FSM()

        ctrl_fsm.act('idle',)