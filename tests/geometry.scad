// Regression fixtures exercise assembled clearances against the actual solid.
include <../lib/parameters.scad>
include <../lib/geometry.scad>
include <../lib/tank.scad>
include <../lib/caps.scad>
include <../lib/tong.scad>
case_name = "paper";
module all_caps() {
    for (i = [0 : chamber_count - 1]) {
        installed_slit_cap(i);
        if (inlets_enabled) installed_inlet_cap(i);
    }
}
module paper_sweep() {
    for (i = [0 : chamber_count - 1])
        translate([(outer_width - paper_width) / 2 - entry_end_clearance,
            slot_yc(i) - paper_thickness / 2 - paper_face_clearance, floor_z + bottom_clearance])
            cube([paper_width + 2 * entry_end_clearance,
                paper_thickness + 2 * paper_face_clearance, outer_height + paper_height]);
}
validate_parameters() {
    if (case_name == "tank") tank();
    else if (case_name == "water") {
        // Outside space plus exactly one separate enclosed volume per chamber.
        // A leak or a cross-connection changes this component count.
        difference() {
            translate([-1, -tank_front - 1, 0.1])
                cube([outer_width + 2, outer_depth + tank_front + tank_back + 2, fill_z - 0.1]);
            tank();
        }
    } else if (case_name == "slit_caps") slit_cap_plate();
    else if (case_name == "inlet_caps") inlet_cap_plate();
    else if (case_name == "tong") tong_plate();
    else {
        // A 1 mm3 sentinel makes an empty intersection exportable.
        translate([-100, -100, -100]) cube(1);
        if (case_name == "paper") intersection() { tank(); paper_sweep(); }
        else if (case_name == "caps") {
            // Lift by a mesh tolerance to exclude intentional face-to-face lid contact.
            intersection() { tank(); translate([0, 0, eps]) all_caps(); }
            if (chamber_count == 2) intersection() { installed_slit_cap(0); installed_slit_cap(1); }
            if (inlets_enabled) for (i = [0 : chamber_count - 1])
                for (j = [0 : chamber_count - 1])
                    intersection() { installed_slit_cap(i); installed_inlet_cap(j); }
        } else if (case_name == "collar") intersection() { tong(); parked_collar(); }
        else if (case_name == "handling") intersection() {
            tank();
            union() for (i = [0 : chamber_count - 1]) immersed_tong(i);
        }
        else if (case_name == "separation") {
            if (chamber_count == 2) intersection() {
                union() { chamber_void(0); inlet_void(0); }
                union() { chamber_void(1); inlet_void(1); }
            }
        } else assert(false, "Unknown geometry test.");
    }
}
