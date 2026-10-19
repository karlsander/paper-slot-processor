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
    else if(check=="central_anchor") strap_anchor_print(retain_mat=true);
    else if(check=="mat_keeper") mat_keeper_print(24);
    else if(check=="cable_saddle") cable_saddle();
    else if(check=="fittings_mat_collision") intersection() { installed_heater_fittings(); heater_mat(); }
    else if(check=="fittings_plate_collision") intersection() {
        installed_heater_fittings();
        // Test the plate interior: the keepers intentionally contact several outer faces.
        translate([(2*cradle_width-spreader_width)/2+0.01,heater_y+0.01,spreader_bottom+0.01])
            cube([spreader_width-0.02,heat_spreader_thickness-0.02,spreader_height-0.02]);
    }
    else if(check=="fittings_cradle_collision") intersection() {
        installed_heater_fittings();
        for(id=[0:1]) translate([id*cradle_width,0,0]) cradle(id);
    }
    else if(check=="fittings_removal") intersection() {
        installed_heater_fittings();
        union() for(id=[0:1]) for(lift=[0:5:75])
            translate([id*cradle_width+vessel_x(id),vessel_y,cradle_floor+lift]) {
                vessel(id); translate([0,0,body_height]) guide(id);
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
        for(id=[0:1]) translate([id*cradle_width+vessel_x(id),vessel_y,cradle_floor]) {
            vessel(id); translate([0,0,body_height]) guide(id);
        }
    }
    else if(check=="holder_collision") intersection() {
        heater_spreader();
        for(id=[0:1]) translate([id*cradle_width+(id==0?8:cradle_width-24),heater_y-12,cradle_floor]) heater_clamp();
    }
    else assert(false,"Unknown probe");
}
