module sim_top
    (
        input sys_clk,
        input sys_rst,
        inout sio3
    );


TristateModelHand tmh(
    .clk(sys_clk),
    .rst(sys_rst),
    .sio3(sio3)
);


// the "macro" to dump signals
`ifdef COCOTB_SIM_DUMP_VCD_VERILOG
initial begin
  $dumpfile (`COCOTB_SIM_DUMP_VCD_VERILOG);
  $dumpvars (0, `COCOTB_SIM_DUMP_VCD_VERILOG_TOPLEVEL);
  #1;
end
`endif

endmodule

