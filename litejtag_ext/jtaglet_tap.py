# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations
from typing import Final

from rich import print

from migen import *
from migen.fhdl.specials import Special

from .data import jtaglet as data_mod
from importlib_resources import files
_JTAGLET_TAP_VERILOG_NAMES: Final = ('ff_sync.v', 'jtag_reg.v', 'jtag_state_machine.v', 'jtaglet.v')
_JTAGLET_TAP_VERILOG_PATHS: Final = [files(data_mod).joinpath(n) for n in _JTAGLET_TAP_VERILOG_NAMES]


class JtagletJTAGTAPImpl(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):

        # # #

        self.specials += Instance("jtaglet",
              i_tms  = tms,
              i_tck  = tck,
              i_trst = trst,
              i_tdi  = tdi,
              o_tdo  = tdo,
          )


class JtagletJTAGTAP(Special):
    def __init__(self, platform, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):
        super().__init__()
        self.tms = tms
        self.tck = tck
        self.tdi = tdi
        self.tdo = tdo
        self.trst = trst

        for p in _JTAGLET_TAP_VERILOG_PATHS:
            platform.add_source(str(p), 'veriliog')

    @staticmethod
    def lower(dr):
        return JtagletJTAGTAPImpl(dr.tms, dr.tck, dr.tdi, dr.tdo, dr.trst)
