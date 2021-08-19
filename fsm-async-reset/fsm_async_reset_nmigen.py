#!/usr/bin/env python3

from nmigen import *
from nmigen.cli import main


class FSMResetNmigen(Elaboratable):
    def __init__(self):
        self.ctr = Signal(16)


    def elaborate(self, platform):
        m = Module()

        m.d.sync += self.ctr.eq(self.ctr + 1)

        with m.FSM() as fsm:
            with m.State('standby'):
                m.next = 'cmd'
            with m.State('cmd'):
                m.next = 'standby'

        return m


if __name__ == "__main__":
    rx = FSMResetNmigen()
    main(rx)
