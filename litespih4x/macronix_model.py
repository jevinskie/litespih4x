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
    def __init__(self, sclk: Signal, rst: Signal, csn: Signal, psink: Signal,
                 si_i: Signal, si_o: Signal,
                 so_o: Signal, so_i: Signal,
                 wp_o: Signal, wp_i: Signal,
                 sio3_i: Signal, sio3_o: Signal):
        self.rstn = rstn = ~rst

        # # #

        self.specials += Instance("MX25U25635F",
              i_PSINK = psink,
              i_RESET = rstn,
              i_SCLK = sclk,
              i_CS = csn,
              i_SI_i = si_i,
              i_SO_i = so_i,
              i_WP_i = wp_i,
              i_SIO3_i = sio3_i,
              o_SI_o = si_o,
              o_SO_o = so_o,
              o_WP_o = wp_o,
              o_SIO3_o = sio3_o,
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
