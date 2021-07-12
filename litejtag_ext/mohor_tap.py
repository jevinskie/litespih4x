# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations

from rich import print

from migen import *
from migen.fhdl.specials import Special

from . import data as data_mod
from importlib_resources import files
_MOHOR_TAP_VERILOG_NAME: Final = 'tap_top.v'
_MOHOR_TAP_VERILOG_PATH: Final = files(data_mod).joinpath(_MOHOR_TAP_VERILOG_NAME)


class MohorJTAGTAPImpl(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal):
        self.tck = Signal()
        self.tms = Signal()
        self.tdi = Signal()
        self.tdo = Signal()

        # # #

        self.specials += Instance("tap_top",
              i_tms_pad_i  = self.tms,
              i_tck_pad_i  = self.tck,
              i_trst_pad_i = 0,
              i_tdi_pad_i  = self.tdi,
              o_tdo_pad_o  = self.tdo,
          )


class MohorJTAGTAP(Special):
    def __init__(self, platform, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal):
        super().__init__()
        self.tms = tms
        self.tck = tck
        self.tdi = tdi
        self.tdo = tdo

        platform.add_source(str(_MOHOR_TAP_VERILOG_PATH), 'veriliog)')

    @staticmethod
    def lower(dr):
        return MohorJTAGTAPImpl(dr.tms, dr.tck, dr.tdi, dr.tdo)
