// Print broad OUTSIDE faces on the bed, plugs up; flip for use. No supported handles.
module slit_cap() {
    union() {
        hull() for (x = [-entry_straight / 2, entry_straight / 2])
            translate([x, 0, 0]) cylinder(h = cap_lid_thickness, r = slit_cap_radius);
        translate([entry_straight / 2, -slit_lid_width / 2, 0])
            cube([slit_cap_radius + cap_tab_length, slit_lid_width, cap_lid_thickness]);
        // Match the actual entry's capsule ends and taper, inset on all sides.
        hull() {
            capsule_slice(-entry_straight / 2, entry_straight / 2, 0,
                cap_lid_thickness - eps, mouth_radius - cap_clearance);
            capsule_slice(-entry_straight / 2, entry_straight / 2, 0,
                cap_lid_thickness + top_round, entry_mouth_width / 2 - cap_clearance);
        }
        hull() {
            capsule_slice(-entry_straight / 2, entry_straight / 2, 0,
                cap_lid_thickness + top_round - eps, entry_mouth_width / 2 - cap_clearance);
            capsule_slice(-entry_straight / 2, entry_straight / 2, 0,
                cap_lid_thickness + slit_cap_rib_depth - eps,
                entry_radius_at_depth(slit_cap_rib_depth) - cap_clearance);
        }
    }
}
module inlet_cap() {
    r = inlet_opening_diameter / 2 - cap_clearance;
    chamfer = min(1, inlet_plug_length / 3);
    union() {
        cylinder(h = cap_lid_thickness, r = inlet_cap_radius);
        hull() for (y = [inlet_cap_radius - 5, inlet_cap_radius + cap_tab_length - 5])
            translate([0, y, 0]) cylinder(h = cap_lid_thickness, r = 5);
        translate([0, 0, cap_lid_thickness - eps])
            cylinder(h = inlet_plug_length - chamfer + eps, r = r);
        translate([0, 0, cap_lid_thickness + inlet_plug_length - chamfer])
            cylinder(h = chamfer, r1 = r, r2 = r - chamfer);
    }
}
module installed_slit_cap(i) {
    translate([outer_width / 2, slot_yc(i), outer_height + cap_lid_thickness])
        rotate([180, 0, i == 0 ? 0 : 180]) slit_cap();
}
module installed_inlet_cap(i) {
    inlet_frame(i) translate([0, -inlet_offset, outer_height + cap_lid_thickness])
        rotate([180, 0, 0]) inlet_cap();
}
module slit_cap_plate() {
    for (i = [0 : chamber_count - 1])
        translate([0, i * (slit_lid_width + plate_gap), 0]) slit_cap();
}
module inlet_cap_plate() {
    for (i = [0 : chamber_count - 1])
        translate([i * (2 * inlet_cap_radius + plate_gap), 0, 0]) inlet_cap();
}
