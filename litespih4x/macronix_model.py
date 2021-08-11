# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import annotations
from typing import Final

from rich import print

from migen import *
from migen.fhdl.specials import Special

from .data import macronix as data_mod
from importlib_resources import files
_MODEL_VERILOG_NAME: Final = 'MX25U25635F.v'
_MODEL_TAP_VERILOG_PATH: Final = files(data_mod).joinpath(_MODEL_VERILOG_NAME)


class MacronixModelImpl(Module):
    def __init__(self, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):
        # module
        # MX25U25635F(SCLK,
        #             CS,
        #             SI,
        #             SO,
        #             WP,
        #        `ifdef MX25U25635FM
        #             RESET,
        #        `endif
        #             SIO3 );

        # # #

        self.specials += Instance("tap_top",
              i_SCLK = tms,
              i_CS = tck,
              i_SI = trst,
              o_SO = tdi,
              i_WP = wp,
              i_SIO3 = tdo,
          )


class MacronixModel(Special):
    def __init__(self, platform, tms: Signal, tck: Signal, tdi: Signal, tdo: Signal, trst: Signal):
        super().__init__()
        self.tms = tms
        self.tck = tck
        self.tdi = tdi
        self.tdo = tdo
        self.trst = trst

        platform.add_source(str(_MODEL_TAP_VERILOG_PATH), 'veriliog')

    @staticmethod
    def lower(dr):
        return MacronixModelImpl(dr.tms, dr.tck, dr.tdi, dr.tdo, dr.trst)
