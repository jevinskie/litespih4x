# Makefile

# defaults
SIM ?= icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES += $(PWD)/tap_top.v

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = tap_top

# MODULE is the basename of the Python test file
MODULE = test_jtag

DUMP_VCD = 1

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
