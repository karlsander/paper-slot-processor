// Geometry probes used by scripts/check_durst_geometry.py; not a print file.
include <carrier.scad>
check = "collision";
angle = 0;

if (check == "collision") {
    intersection() { c35_a(); c35_b(angle); }
} else if (check == "window") {
    // Independently specified nominal optical opening through the assembly.
    intersection() {
        union() { c35_a(); c35_b(); }
        translate([-18, 42, -20]) cube([36, 24, 40]);
    }
} else if (check == "film") {
    // A 90 mm long strip, nominally 35 wide and 0.14 thick, including the
    // regions beside both guide pins. A small vertical offset avoids coplanarity.
    intersection() {
        union() { c35_a(); c35_b(); }
        translate([-45, 36.5, 0.02]) cube([90, 35, 0.14]);
    }
} else if (check == "window_dimensions_a") {
    // Slice of the hole at the film surface, clipped away from the outside.
    difference() {
        translate([-25, 35, -0.2]) cube([50, 38, 0.1]);
        c35_a();
    }
} else if (check == "b_corner_insets") {
    // Four small probes outside the nominal corners must meet B's insets.
    intersection() {
        c35_b_local();
        for (x=[-18.4, 18.2], y=[41.6, 66.2])
            translate([x, y, 0.05]) cube([0.2, 0.2, 0.2]);
    }
} else if (check == "b_relief") {
    // Relief must be open beyond the midpoint of all four nominal edges.
    intersection() {
        c35_b_local();
        union() {
            for (x=[-18.5, 18.3]) translate([x, 53, 0.05]) cube([0.2, 2, 0.2]);
            for (y=[41.5, 66.3]) translate([-1, y, 0.05]) cube([2, 0.2, 0.2]);
        }
    }
} else {
    assert(false, "Unknown carrier check");
}
