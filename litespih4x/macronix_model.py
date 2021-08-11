# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations
from typing import Final

from rich import print

from migen import *
from migen.fhdl.specials import Special

from .data import mohor as data_mod
from importlib_resources import files
_MOHOR_TAP_VERILOG_NAME: Final = 'tap_top.v'
_MOHOR_TAP_VERILOG_PATH: Final = files(data_mod).joinpath(_MOHOR_TAP_VERILOG_NAME)


class MohorJTAGTAPImpl(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):

        # # #

        self.specials += Instance("tap_top",
              i_tms_pad_i  = tms,
              i_tck_pad_i  = tck,
              i_trst_pad_i = trst,
              i_tdi_pad_i  = tdi,
              o_tdo_pad_o  = tdo,
          )


class MohorJTAGTAP(Special):
    def __init__(self, platform, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):
        super().__init__()
        self.tms = tms
        self.tck = tck
        self.tdi = tdi
        self.tdo = tdo
        self.trst = trst

        platform.add_source(str(_MOHOR_TAP_VERILOG_PATH), 'veriliog')

    @staticmethod
    def lower(dr):
        return MohorJTAGTAPImpl(dr.tms, dr.tck, dr.tdi, dr.tdo, dr.trst)
