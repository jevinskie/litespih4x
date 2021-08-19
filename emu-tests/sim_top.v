module sim_top
    (
        input sys_clk,
        input sys_rst,
        inout sio3
    );

tstate_sim tss(
    .sys_clk(sys_clk),
    .sys_rst(sys_rst),
    .sio3(sio3)
);

`ifdef UNDEF
TristateModelHand tmh(
    .sys_clk(sys_clk),
    .sys_rst(sys_rst),
    .sio3(sio3)
);
`endif


// the "macro" to dump signals
`ifdef COCOTB_SIM_DUMP_VCD_VERILOG
initial begin
  $dumpfile (`COCOTB_SIM_DUMP_VCD_VERILOG);
  $dumpvars (0, `COCOTB_SIM_DUMP_VCD_VERILOG_TOPLEVEL);
  #1;
end
`endif

endmodule

