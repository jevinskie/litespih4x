#!/usr/bin/env python3

from migen import *
from migen.fhdl import verilog

class FSMBug(Module):
    def __init__(self):
        self.submodules.ctrl_fsm = ctrl_fsm = FSM(reset_state='standby')
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
    m = FSMBug()
    print(verilog.convert(m,))
