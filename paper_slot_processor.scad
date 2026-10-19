// Tank export. Edit lib/parameters.scad to change all matching parts together.
include <lib/parameters.scad>
include <lib/geometry.scad>
include <lib/tank.scad>
include <lib/caps.scad>
include <lib/tong.scad>
view = "tank"; // [tank,assembly,section,fit,handling]
validate_parameters() {
    echo(tank_mm = [outer_width, outer_depth + tank_front + tank_back, outer_height],
        paper_entry_mm = [entry_length, paper_slit_width], max_paper_mm = [max_paper_width, max_paper_height]);
    echo(nominal_bath_ml = nominal_bath_ml, volume_label = volume_label, mix_label = mix_label);
    if (view == "tank") tank();
    else if (view == "assembly") {
        color("SteelBlue") tank();
        for (i = [0 : chamber_count - 1]) {
            color("Goldenrod") installed_slit_cap(i);
            if (inlets_enabled) color("Goldenrod") installed_inlet_cap(i);
        }
    } else if (view == "handling") {
        color("SteelBlue") tank();
        color("Goldenrod") immersed_tong(0);
        color([1, 1, 1, 0.5]) translate([(outer_width - paper_width) / 2,
            slot_yc(0) - paper_thickness / 2, fill_z - paper_height])
                cube([paper_width, paper_thickness, paper_height]);
    } else if (view == "fit") {
        // Full-width top section for checking paper entry and both cap fits cheaply.
        cut_z = pool_z - inlet_wall - 3;
        translate([0, 0, -cut_z]) intersection() {
            tank();
            translate([-1, -tank_front - 1, cut_z])
                cube([outer_width + 2, outer_depth + tank_front + tank_back + 2, outer_height]);
        }
    } else if (view == "section") {
        difference() {
            tank();
            translate([outer_width / 2, -tank_front - 1, -1])
                cube([outer_width, outer_depth + tank_front + tank_back + 2, outer_height + 2]);
        }
    } else assert(false, "view must be tank, assembly, section, fit or handling.");
}
