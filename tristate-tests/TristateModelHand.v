/* Machine-generated using Migen */
module TristateModelHand(
	inout sio3,
	input sys_clk,
	input sys_rst
);

wire o;
wire oe;
wire i;
reg [1:0] cnt = 2'd0;

// synthesis translate_off
reg dummy_s;
initial dummy_s <= 1'd0;
// synthesis translate_on

assign oe = cnt[0];
assign o = cnt[1];

always @(posedge sys_clk) begin
	cnt <= (cnt + 1'd1);
	if (sys_rst) begin
		cnt <= 2'd0;
	end
end

assign sio3 = oe ? o : 1'bz;
assign i = sio3;

endmodule