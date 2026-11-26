`timescale 1ns/1ps
module tb_ring_readout;
    reg clk = 0, rst_n = 1, meas_en = 1, ro_en = 1;
    reg [9:0] addr = 0;
    reg [7:0] ro_clk = 0;
    wire ready, ro_out;
    wire [63:0] bank_enable;
    wire [15:0] member_enable;
    wire [7:0] ring_enable;
`ifdef CHECK_RING_CUTS
    localparam [1023:0] cuts = (1024'b1 << 482) | (1024'b1 << 996);
    cryo_char_ctrl #(.CUT_PATHS(cuts)) dut (.*);
`else
    cryo_char_ctrl dut (.*);
`endif

    integer channel, pulse;
    reg [9:0] ring_address [0:7];

    task select_tick;
        begin #5; clk = 1; #5; clk = 0; #5; end
    endtask
    task edges(input [7:0] mask);
        begin ro_clk = mask; #5; ro_clk = 0; #5; end
    endtask
    task check_output(input expected);
        begin
            if (ro_out !== expected)
                $fatal(1, "channel=%0d pulse=%0d expected RO_OUT=%b, saw %b",
                       channel, pulse, expected, ro_out);
        end
    endtask
    task select_ring(input [9:0] code, input [7:0] mask);
        begin
            addr = code;
            select_tick;
            if ({ready,ring_enable,ro_out} !== 10'b0)
                $fatal(1,"missing blank before %0d",code);
            select_tick;
            if ({ready,ring_enable} !== {1'b1,mask} ||
                bank_enable !== (64'b1 << code[9:4]) ||
                member_enable !== (16'b1 << code[3:0]))
                $fatal(1,"wrong physical selection for %0d",code);
        end
    endtask
`ifdef CHECK_RING_CUTS
    task check_cut(input [9:0] code);
        begin
            addr = code;
            repeat (3) begin
                select_tick;
                if ({ready, bank_enable, member_enable, ring_enable, ro_out} !== 90'b0)
                    $fatal(1, "cut address %0d reached a physical path", code);
            end
            repeat (1030) begin edges(8'hff); check_output(0); end
        end
    endtask
`endif
    initial begin
        ring_address[0]=482; ring_address[1]=483; ring_address[2]=484; ring_address[3]=487;
        ring_address[4]=994; ring_address[5]=995; ring_address[6]=996; ring_address[7]=999;
        #1; rst_n = 0; #5; check_output(0); rst_n = 1;
`ifdef CHECK_RING_CUTS
        check_cut(482);
        select_ring(994, 8'h10);  // Uncut replica of the cut primary.
        repeat (514) edges(8'h10);
        check_output(1);
        check_cut(996);
        select_ring(484, 8'h04);  // Uncut primary of the cut replica.
        repeat (514) edges(8'h04);
        check_output(1);
        $display("PASS frozen primary and replica isolated, opposite specimens live");
        $finish;
`endif
        for (channel=0; channel<8; channel=channel+1) begin
            select_ring(ring_address[channel], 8'b1 << channel);
            // More than a divided period of noise on every other input.
            repeat (1030) begin edges(~(8'b1 << channel)); check_output(0); end
            // Release consumes two edges. Check every phase through two full
            // periods, then stop high to exercise the asynchronous clear.
            for (pulse=1; pulse<=2562; pulse=pulse+1) begin
                edges(8'b1 << channel);
                check_output(pulse>2 && (((pulse-2)/512)%2 == 1));
            end
            case (channel % 4)
                0: begin ro_en=0; #5; check_output(0); ro_en=1; end
                1: begin meas_en=0; #5; check_output(0); meas_en=1;
                         select_ring(ring_address[channel], 8'b1 << channel); end
                2: begin rst_n=0; #5; check_output(0); rst_n=1;
                         select_ring(ring_address[channel], 8'b1 << channel); end
                3: begin select_ring(510, 0); check_output(0);
                         select_ring(ring_address[channel], 8'b1 << channel); end
            endcase
            #2; check_output(0);
            for (pulse=1; pulse<=514; pulse=pulse+1) begin
                edges(8'b1 << channel); check_output(pulse == 514);
            end
        end
        select_ring(1, 0);
        repeat (1050) begin edges(8'hff); check_output(0); end
        $display("PASS eight physical ring channels, divide by 1024, stop and restart");
        $finish;
    end
endmodule
