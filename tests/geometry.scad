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
    else if (case_name == "water" || case_name == "loaded_water" || case_name == "fill_water" ||
            case_name == "cue_water" || case_name == "below_cue_water" || case_name == "low_water") {
        echo(volume_check = [nominal_bath_ml, working_volume_ml, mix_first_ml, mix_second_ml, nominal_empty_ml]);
        echo(fill_check = [working_fill_z, loaded_fill_z, indicator_depth, indicator_volume_ml]);
        level = case_name == "loaded_water" ? max_fill_z :
            case_name == "fill_water" ? loaded_fill_z :
            case_name == "cue_water" ? working_fill_z :
            case_name == "below_cue_water" ? pool_z - 0.5 :
            case_name == "low_water" ? inlet_exit_z + 1 : fill_z;
        // Outside space plus exactly one separate enclosed volume per chamber.
        // A leak or a cross-connection changes this component count.
        difference() {
            translate([-1, -tank_front - 1, 0.1])
                cube([outer_width + 2, outer_depth + tank_front + tank_back + 2,
                    level - 0.1]);
            tank();
            // Check working fill and remaining headroom with the paper inserted.
            if (case_name == "loaded_water" || case_name == "fill_water") for (i = [0 : chamber_count - 1]) {
                translate([(outer_width - paper_width) / 2,
                    slot_yc(i) - paper_thickness / 2, paper_bottom_z])
                    cube([paper_width, paper_thickness, paper_height]);
            }
        }
    } else if (case_name == "inlet") inlet_frame(0) inlet_loft();
    else if (case_name == "sight_pool") {
        echo(indicator_check = [indicator_depth, indicator_volume_ml]);
        intersection() {
            inlet_void(0);
            translate([0, -tank_front, pool_z]) cube([outer_width, tank_front, indicator_depth]);
        }
    } else if (case_name == "inlet_flow") {
        translate([-100, -100, -100]) cube(1);
        intersection() {
            tank();
            inlet_frame(0) for (j = [0 : len(inlet_stations) - 2])
                if (max(inlet_stations[j][1], inlet_stations[j + 1][1]) <= wall_thickness + slot_gap / 2)
                    hull() for (s = [inlet_stations[j], inlet_stations[j + 1]])
                        translate([0, s[1], s[0]])
                            sphere(r = min(4.5, inlet_bore_diameter / (2 * sqrt(2)) - 0.2, slot_gap / 2 - 0.5), $fn = 32);
        }
    } else if (case_name == "rounding") {
        assert(rounded_working_ml(209.3, [1, 4], 2) == 210);
        assert(whole_mix_ml(210, [1, 4]) == [42, 168]);
        assert(rounded_working_ml(207.4, [1, 4], 2) == 207);
        assert(rounded_working_ml(212.5, [1, 4], 2) == 213);
        assert(rounded_working_ml(209.3, [2, 8], 2) == 210);
        assert(rounded_working_ml(273.7, [1, 4], 2, 274.3) == 274);
        assert(rounded_working_ml(209.3, [1, 4], 2, 215, 211) == 211);
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
