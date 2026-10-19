include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v2/guide.scad>
include <../v2/cradle.scad>
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
    else if(check=="empty_water") water(id=chamber);
    else if(check=="loaded_water") water(loaded_level,true,id=chamber);
    else if(check=="low_water") water(well_exit_z+3,id=chamber);
    else if(check=="paper_collision") intersection() {
        swept_paper();
        union() { vessel(chamber); translate([0,0,body_height]) guide(chamber); }
    }
    else if(check=="probe_collision") intersection() {
        swept_paper();
        translate([wall+probe_diameter/2+0.25,body_depth/2,body_height-60])
            cylinder(d=probe_diameter,h=60+guide_thickness);
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
