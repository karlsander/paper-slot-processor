// Simple push-in cap for paper_slot_processor.scad chemistry inlets.
//
// Print upright with the plug on the bed. The plug is intentionally a little
// undersized for a first test; reduce cap_clearance for a tighter fit.
//
// Units: millimeters.

$fn = 64;

// Match these to the inlet settings in paper_slot_processor.scad.
inlet_opening_diameter = 30;   // funnel mouth bore (cap plug seats in this)
inlet_cap_land_height = 10;
inlet_wall_top = 2;            // thin wall at the mouth; flange rests on this rim

// Fit and cap geometry.
cap_clearance = 0.35;
cap_plug_length = max(2, inlet_cap_land_height - 1);
cap_plug_bottom_chamfer = 1.2;
cap_shoulder_slope = 1;
cap_flange_height = 3;
cap_flange_overhang = 5;
cap_pull_height = 16;
cap_pull_diameter_bottom = 18;
cap_pull_diameter_top = 14;

plug_diameter = inlet_opening_diameter - 2 * cap_clearance;
flange_diameter = inlet_opening_diameter + 2 * inlet_wall_top + 2 * cap_flange_overhang;
shoulder_height = (flange_diameter - plug_diameter) / 2 * cap_shoulder_slope;

module inlet_cap() {
    union() {
        cylinder(
            h = cap_plug_bottom_chamfer,
            d1 = plug_diameter - 2 * cap_plug_bottom_chamfer,
            d2 = plug_diameter
        );

        translate([0, 0, cap_plug_bottom_chamfer])
            cylinder(
                h = cap_plug_length - cap_plug_bottom_chamfer,
                d = plug_diameter
            );

        translate([0, 0, cap_plug_length])
            cylinder(
                h = shoulder_height,
                d1 = plug_diameter,
                d2 = flange_diameter
            );

        translate([0, 0, cap_plug_length + shoulder_height])
            cylinder(
                h = cap_flange_height,
                d = flange_diameter
            );

        translate([0, 0, cap_plug_length + shoulder_height + cap_flange_height])
            cylinder(
                h = cap_pull_height,
                d1 = cap_pull_diameter_bottom,
                d2 = cap_pull_diameter_top
            );
    }
}

inlet_cap();
