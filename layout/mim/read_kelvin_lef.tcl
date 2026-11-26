# Report the dimensions and access rectangles as consumed by OpenROAD.
read_lef $tech_lef
read_lef $macro_lef
set database [ord::get_db]
set library [lindex [$database getLibs] end]
set units [[$database getTech] getDbUnitsPerMicron]
puts "UNITS $units"
foreach master [$library getMasters] {
    set cell [$master getName]
    puts "SIZE $cell [$master getWidth] [$master getHeight]"
    foreach terminal [$master getMTerms] {
        foreach port [$terminal getMPins] {
            foreach box [$port getGeometry] {
                set layer [[$box getTechLayer] getName]
                puts "PIN $cell [$terminal getName] $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
            }
        }
    }
    foreach box [$master getObstructions] {
        set layer [[$box getTechLayer] getName]
        puts "OBS $cell $layer [$box xMin] [$box yMin] [$box xMax] [$box yMax]"
    }
}
