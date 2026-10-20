include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v2/guide.scad>
include <../v2/cradle.scad>
include <../v2/heater.scad>
check="vessel";
chamber=0;
module swept_paper() {
    hull() for(lift=[0.03,vertical_stroke]) for(side=[-lateral_stroke,lateral_stroke])
        paper(lift,side);
}
valid() {
    raised_level=level_for_volume(working_ml*1000,true,lift=vertical_stroke);
    echo(check_values=[working_ml,empty_level,loaded_level,raised_level,
        image_top+vertical_stroke,body_height,trim_band,paper_cut_length,
        actual_sight_depth,visible_pool_ml,amounts_a,amounts_b]);
    if(check=="vessel") vessel_print(chamber);
    else if(check=="guide") guide_print(chamber);
    else if(check=="cover") guide_print(chamber,closed=true);
    else if(check=="clip") clip_print();
    else if(check=="cradle") cradle(chamber);
    else if(check=="link") cradle_link();
    else if(check=="heater_clamp") heater_clamp();
    else if(check=="guard_tile") guard_tile();
    else if(check=="guard_link") guard_link();
    else if(check=="guard_mount") guard_mount_print();
    else if(check=="strap_anchor") strap_anchor_print();
    else if(check=="mat_keeper") mat_keeper_print(24);
    else if(check=="cable_saddle") cable_saddle();
    else if(check=="fittings_mat_collision") intersection() { installed_heater_fittings(chamber); heater_mat(); }
    else if(check=="fittings_plate_collision") intersection() {
        installed_heater_fittings(chamber);
        // Test the plate interior: the keepers intentionally contact several outer faces.
        translate([spreader_left+0.01,heater_y+0.01,spreader_bottom+0.01])
            cube([spreader_width-0.02,heat_spreader_thickness-0.02,spreader_height-0.02]);
    }
    else if(check=="fittings_cradle_collision") intersection() {
        installed_heater_fittings(chamber);
        cradle(chamber);
    }
    else if(check=="fittings_removal") intersection() {
        installed_heater_fittings(chamber);
        union() for(lift=[0:5:75]) vessel_position(chamber,lift) {
            vessel(chamber); translate([0,0,body_height]) guide(chamber);
        }
    }
    else if(check=="empty_water") water(id=chamber);
    else if(check=="loaded_water") water(loaded_level,true,id=chamber);
    else if(check=="low_water") water(well_exit_z+3,id=chamber);
    else if(check=="paper_collision") intersection() {
        swept_paper();
        union() { vessel(chamber); translate([0,0,body_height]) guide(chamber); }
    }
    else if(check=="guide_collision") intersection() {
        vessel(chamber); translate([0,0,body_height]) guide(chamber);
    }
    else if(check=="clip_collision") intersection() {
        installed_clips(); union() { vessel(chamber); translate([0,0,body_height]) guide(chamber); }
    }
    else if(check=="cradle_removal") intersection() {
        cradle(chamber);
        union() for(lift=[0:2:50])
            translate([vessel_x(chamber),vessel_y,cradle_floor+lift]) vessel(chamber);
    }
    else if(check=="heater_collision") intersection() {
        heater_spreader();
        vessel_position(chamber) {
            vessel(chamber); translate([0,0,body_height]) guide(chamber);
        }
    }
    else if(check=="holder_collision") intersection() {
        heater_spreader();
        installed_heater_clamps();
    }
    else if(check=="fittings_clamp_collision") intersection() {
        installed_heater_fittings(chamber); installed_heater_clamps();
    }
    else if(check=="module_collision") intersection() {
        union() { cradle(0); installed_heater_clamps(); installed_heater_fittings(0);
            heater_spreader(); heater_mat(); vessel_position(0) vessel(0); }
        module_position(1) union() { cradle(1); installed_heater_clamps(); installed_heater_fittings(1);
            heater_spreader(); heater_mat(); vessel_position(1) vessel(1); }
    }
    else assert(false,"Unknown probe");
}
