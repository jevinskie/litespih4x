#!/usr/bin/env python3

from migen import *
from migen.fhdl import verilog
from migen.genlib.resetsync import AsyncResetSynchronizer

class FSMResetMigen(Module):
    def __init__(self):
        self.clock_domains.cd_sys = cd_sys = ClockDomain()
        self.specials += AsyncResetSynchronizer(cd_sys, ResetSignal())

        ctrl_fsm = FSM(reset_state='standby')

        # ctrl_fsm = ResetInserter()(ctrl_fsm)
        # self.comb += ctrl_fsm.reset.eq(ResetSignal())

        self.submodules.ctrl_fsm = ctrl_fsm

        ctrl_fsm.act('standby',
            NextState('cmd'),
        )
        ctrl_fsm.act('cmd',
            NextState('standby'),
        )

        self.cnt = cnt = Signal(16)
        self.sync += cnt.eq(cnt + 1)

# initial begin
#   $dumpfile ("dump.vcd");
#   $dumpvars (0, top);
#   #1;
# end

if __name__ == "__main__":
    m = FSMResetMigen()
    print(verilog.convert(m,))
