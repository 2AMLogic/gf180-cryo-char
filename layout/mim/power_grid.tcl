read_lef $tech_lef
read_lef $macro_lef
read_verilog $verilog
link_design cryo_grid_trial
initialize_floorplan -site GF018hv5v_mcu_sc7 -die_area {0 0 3932 5122} -core_area $core_area
make_tracks
foreach {code x y} {452 860 4310 453 2475 4300 454 625 3100 455 2090 3100} {
    place_macro -macro_name spec_$code -location [list $x $y] -orientation R0 -exact
}
set block [ord::get_db_block]
foreach {name kind} {VDD POWER VSS GROUND} {
    set net [odb::dbNet_create $block $name]
    $net setSigType $kind
    $net setSpecial
}
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core_grid -voltage_domains CORE -starts_with POWER
add_pdn_ring -grid core_grid -layers {Metal4 Metal5} -widths {25 25} -spacings {1.7 1.7} -core_offsets {6 6}
add_pdn_stripe -grid core_grid -layer Metal4 -width 5 -pitch 75 -spacing 1 -offset 13.82 -starts_with POWER -extend_to_core_ring
add_pdn_stripe -grid core_grid -layer Metal5 -width 5 -pitch 75 -spacing 1 -offset 14.15 -starts_with POWER -extend_to_core_ring
add_pdn_connect -grid core_grid -layers {Metal4 Metal5}
pdngen
check_power_grid -net VDD -dont_require_terminals
check_power_grid -net VSS -dont_require_terminals

# Export every cut and enclosure with its physical location in database units.
set out [open $geometry w]
puts $out "UNITS [$block getDbUnitsPerMicron]"
foreach inst [$block getInsts] {
    set box [$inst getBBox]
    puts $out "MACRO [[$inst getMaster] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
}
proc rectangle {out net box dx dy} {
    set layer [[$box getTechLayer] getName]
    puts $out "$net $layer [expr {[$box xMin] + $dx}] [expr {[$box yMin] + $dy}] [expr {[$box xMax] + $dx}] [expr {[$box yMax] + $dy}]"
}
foreach rail {VDD VSS} {
    foreach wire [[$block findNet $rail] getSWires] {
        foreach shape [$wire getWires] {
            if {[$shape isVia]} {
                lassign [$shape getViaXY] x y
                foreach box [[$shape getBlockVia] getBoxes] {
                    rectangle $out $rail $box $x $y
                }
            } else {
                rectangle $out $rail $shape 0 0
            }
        }
    }
}
close $out
