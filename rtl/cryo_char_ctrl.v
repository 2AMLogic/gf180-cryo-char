`timescale 1ns/1ps
`default_nettype none

module cryo_char_ctrl #(
    parameter [1023:0] CUT_PATHS = 1024'b0
) (
    input  wire clk, rst_n, meas_en, ro_en,
    input  wire [9:0] addr,
    // One buffered, logic-domain clock per physical oscillator specimen.
    input  wire [7:0] ro_clk,
    output wire ready, ro_out,
    output wire [63:0] bank_enable,
    output wire [15:0] member_enable,
    output wire [7:0] ring_enable
);
    cryo_selector #(.CUT_PATHS(CUT_PATHS)) select_path (
        .clk(clk), .rst_n(rst_n), .meas_en(meas_en), .addr(addr), .ro_en(ro_en),
        .ready(ready), .bank_enable(bank_enable), .member_enable(member_enable),
        .ring_enable(ring_enable)
    );

    wire [7:0] divided;
    genvar i;
    generate for (i = 0; i < 8; i = i + 1) begin : ring
        // Clear with the ring stopped. Release in its own clock domain.
        (* async_reg = "true" *) reg [1:0] armed;
        always @(posedge ro_clk[i] or negedge ring_enable[i]) begin
            if (!ring_enable[i])
                armed <= 2'b00;
            else
                armed <= {armed[0], 1'b1};
        end

        reg [9:0] count;
        always @(posedge ro_clk[i] or negedge armed[1]) begin
            if (!armed[1])
                count <= 10'd0;
            else
                count <= count + 1'b1;
        end
        assign divided[i] = count[9] & ring_enable[i];
    end endgenerate

    assign ro_out = |divided;
endmodule

`default_nettype wire
