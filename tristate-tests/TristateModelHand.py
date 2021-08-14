#!/usr/bin/env python3

from migen import *
from migen.fhdl import verilog


class TristateModelHand(Module):
    def __init__(self, sio3: Signal, xor_oe=0, xor_o=0):
        self.sio3 = sio3
        self.sio3_ts = sio3_ts = TSTriple()
        self.specials += self.sio3_ts.get_tristate(self.sio3)

        self.cnt = cnt = Signal(2)

        self.sync += cnt.eq(cnt + 1)

        self.comb += sio3_ts.oe.eq(cnt[0] ^ xor_oe)
        self.comb += sio3_ts.o.eq(cnt[1] ^ xor_o)

if __name__ == "__main__":
    sio3 = Signal()
    tms = TristateModelHand(sio3)
    print(verilog.convert(tms, name=tms.__class__.__name__, ios={tms.sio3}))
