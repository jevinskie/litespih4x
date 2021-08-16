# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
# Simple tests for an adder module
import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock

def fork_clk():
    cocotb.fork(Clock(cocotb.top.sys_clk, 10, units="ns").start())


@cocotb.test()
async def fsm_clocking_test(dut):
    fork_clk()
    await Timer(100, units='ns')
