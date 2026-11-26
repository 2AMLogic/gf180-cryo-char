`timescale 1ns/1ps
`default_nettype none

// A path conducts only at the intersection of bank_enable and member_enable.
// Set a CUT_PATHS bit to permanently disconnect that physical address at freeze.
module cryo_selector #(
    parameter [1023:0] CUT_PATHS = 1024'b0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        meas_en,
    input  wire [9:0]  addr,
    input  wire        ro_en,
    output wire        ready,
    output reg  [63:0] bank_enable,
    output reg  [15:0] member_enable,
    output wire [7:0]  ring_enable
);
    reg [9:0] pending_addr;
    reg sampled;
    reg [7:0] selected_ring;
    wire [8:0] code = pending_addr[8:0];
    wire replica = pending_addr[9];
    wire enabled = rst_n && meas_en;

    // Primary codes come from spec/structure-map.md. The testbench reads each
    // worksheet entry independently and visits the entire address space.
    wire primary = (code >= 1   && code <= 152) ||
                   (code >= 249 && code <= 418) ||
                   (code >= 421 && code <= 429) ||
                   (code >= 436 && code <= 446) ||
                   (code >= 450 && code <= 463) ||
                   (code >= 465 && code <= 468) ||
                   (code >= 471 && code <= 474) ||
                   (code >= 478 && code <= 484) || code == 487 ||
                   code == 510 || code == 511;
    wire [3:0] ring = {code == 487, code == 484, code == 483, code == 482};
    wire has_replica = (code >= 456 && code <= 463) || (|ring);
    wire supported = primary && (!replica || has_replica) && !CUT_PATHS[pending_addr];

    assign ready = |bank_enable;
    assign ring_enable = selected_ring & {8{ro_en}};

    // Clearing MEAS_EN must open the path with the selection clock stopped.
    // Register the output masks so address-bit skew cannot select a third path
    // when an old request is opened or a new request is made.
    always @(posedge clk or negedge enabled) begin
        if (!enabled) begin
            pending_addr  <= 0;
            sampled       <= 0;
            bank_enable   <= 0;
            member_enable <= 0;
            selected_ring <= 0;
        end else begin
            pending_addr <= addr;
            sampled <= 1;
            if (sampled && addr == pending_addr && supported) begin
                bank_enable   <= 64'b1 << pending_addr[9:4];
                member_enable <= 16'b1 << pending_addr[3:0];
                selected_ring <= replica ? {ring, 4'b0} : {4'b0, ring};
            end else begin
                bank_enable   <= 0;
                member_enable <= 0;
                selected_ring <= 0;
            end
        end
    end
endmodule

`default_nettype wire
