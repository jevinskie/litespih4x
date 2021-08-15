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
                 si: Signal, so: Signal, wp: Signal, sio3: Signal):
        self.csn = csn
        self.si = si
        self.so = so
        self.wp = wp
        self.sio3 = sio3

        self.si_ts = si_ts = TSTriple()
        self.so_ts = so_ts = TSTriple()
        self.wp_ts = wp_ts = TSTriple()
        self.sio3_ts = sio3_ts = TSTriple()


        self.specials += si_ts.get_tristate(si)
        self.specials += so_ts.get_tristate(so)
        self.specials += wp_ts.get_tristate(wp)
        self.specials += sio3_ts.get_tristate(sio3)

        self.submodules.ctrl_fsm = ctrl_fsm = ClockDomainsRenamer('spi')(FSM())

        ctrl_fsm.act('idle',)

        self.cnt = cnt = Signal(16)
        self.sync.spi += cnt.eq(cnt + 1)
