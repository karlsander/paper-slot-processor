// Regression fixtures exercise assembled clearances against the actual solid.
include <../lib/parameters.scad>
include <../lib/geometry.scad>
include <../lib/tank.scad>
include <../lib/caps.scad>
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
            slot_yc(i) - paper_thickness / 2 - eps, paper_bottom_z])
            cube([paper_width + 2 * entry_end_clearance,
                paper_thickness + 2 * eps, outer_height + paper_height]);
}
validate_parameters() {
    if (case_name == "tank") tank();
    else if (case_name == "water" || case_name == "loaded_water" || case_name == "fill_water") {
        echo(volume_check = [nominal_bath_ml, working_volume_ml, mix_first_ml, mix_second_ml, nominal_empty_ml]);
        // Outside space plus exactly one separate enclosed volume per chamber.
        // A leak or a cross-connection changes this component count.
        difference() {
            translate([-1, -tank_front - 1, 0.1])
                cube([outer_width + 2, outer_depth + tank_front + tank_back + 2,
                    (case_name == "loaded_water" ? max_fill_z : fill_z) - 0.1]);
            tank();
            // Check working fill and remaining headroom with the paper inserted.
            if (case_name != "water") for (i = [0 : chamber_count - 1]) {
                translate([(outer_width - paper_width) / 2,
                    slot_yc(i) - paper_thickness / 2, paper_bottom_z])
                    cube([paper_width, paper_thickness, paper_height]);
            }
        }
    } else if (case_name == "rounding") {
        assert(rounded_working_ml(209.3, [1, 4], 2) == 210);
        assert(whole_mix_ml(210, [1, 4]) == [42, 168]);
        assert(rounded_working_ml(207.4, [1, 4], 2) == 207);
        assert(rounded_working_ml(212.5, [1, 4], 2) == 213);
        assert(rounded_working_ml(209.3, [2, 8], 2) == 210);
        assert(rounded_working_ml(273.7, [1, 4], 2, 274.3) == 274);
        for (volume = [200 : 0.1 : 220]) {
            total = rounded_working_ml(volume, [1, 4], 2);
            amounts = whole_mix_ml(total, [1, 4]);
            assert(abs(total - volume) <= 2);
            assert(amounts[0] + amounts[1] == total);
            assert(amounts[0] == floor(amounts[0]) && amounts[1] == floor(amounts[1]));
            assert(abs(amounts[0] - total / 5) <= 0.5);
        }
        cube(1);
    } else if (case_name == "slit_caps") slit_cap_plate();
    else if (case_name == "inlet_caps") inlet_cap_plate();
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
        } else if (case_name == "handling") intersection() {
            tank();
            // Two 18 x 10 mm fingertip envelopes, entirely above the rim.
            union() for (i = [0 : chamber_count - 1]) for (side = [-1, 1])
                translate([outer_width / 2 - 9,
                    slot_yc(i) + (side < 0 ? -paper_thickness / 2 - 10 : paper_thickness / 2),
                    outer_height + 0.5]) cube([18, 10, paper_grip_height - 1]);
        }
        else if (case_name == "separation") {
            if (chamber_count == 2) intersection() {
                union() { chamber_void(0); inlet_void(0); }
                union() { chamber_void(1); inlet_void(1); }
            }
        } else assert(false, "Unknown geometry test.");
    }
}
