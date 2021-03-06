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
    def __init__(self, sclk: Signal, rstn: Signal, csn: Signal,
                 si: Signal, so: Signal, wpn: Signal, sio3: Signal):
        # self.rstn = rstn = ~rst

        # # #

        self.specials += Instance("MX25U25635F",
                                  i_RESET = rstn,
                                  i_SCLK = sclk,
                                  i_CS = csn,
                                  io_SI = si,
                                  io_SO = so,
                                  io_WP = wpn,
                                  io_SIO3 = sio3,
                                  # i_SI_i = si.i,
                                  # i_SO_i = so.i,
                                  # i_WP_i = wp.i,
                                  # i_SIO3_i = sio3.i,
                                  # o_SI_o = si.o,
                                  # o_SO_o = so.o,
                                  # o_WP_o = wp.o,
                                  # o_SIO3_o = sio3.o,
                                  # o_SI_oe = si.oe,
                                  # o_SO_oe = so.oe,
                                  # o_WP_oe = wp.oe,
                                  # o_SIO3_oe = sio3.oe,
                                  )


class MacronixModelSpecial(Special):
    def __init__(self, platform, sclk: Signal, rstn: Signal, csn: Signal,
                 si: Signal, so: Signal, wpn: Signal, sio3: Signal):
        super().__init__()
        self.sclk = sclk
        self.rst = rstn
        self.csn = csn
        self.si = si
        self.so = so
        self.wpn = wpn
        self.sio3 = sio3

        platform.add_source(str(_MODEL_TAP_VERILOG_PATH), 'verilog')

    @staticmethod
    def lower(dr):
        return MacronixModelImpl(dr.sclk, dr.rst, dr.csn, dr.si, dr.so, dr.wpn, dr.sio3)

class MacronixModel(Module):
    def __init__(self, platform, sclk: Signal, rstn: Signal, csn: Signal,
                 si: Signal, so: Signal, wpn: Signal, sio3: Signal):
        # # #

        self.specials += MacronixModelSpecial(platform, sclk, rstn, csn, si, so, wpn, sio3)
