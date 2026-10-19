include <parameters.scad>
include <geometry.scad>
include <vessel.scad>
include <guide.scad>
include <cradle.scad>
part = "vessel";
chamber = 0;
print_layout = false;
valid() {
    echo(image_mm=[roll_width,image_length], cut_mm=[roll_width,paper_cut_length], trim_mm=trim_band);
    echo(vessel_mm=[vessel_xmax,body_depth,body_height], bath_ml=working_ml,
        recipe_a_ml=amounts_a,recipe_b_ml=amounts_b,fill_levels=[empty_level,loaded_level],
        cue=[actual_sight_depth,visible_pool_ml],agitation=[vertical_stroke,lateral_stroke]);
    if(part=="vessel") { if(print_layout) vessel_print(chamber); else vessel(chamber); }
    else if(part=="guide") { if(print_layout) guide_print(chamber); else translate([0,0,guide_skirt]) guide(chamber); }
    else if(part=="cover") guide_print(chamber,closed=true);
    else if(part=="clip") clip_print();
    else if(part=="clips") for(x=[0,14]) for(y=[0,14]) translate([x,y,0]) clip_print();
    else if(part=="cradle") cradle(chamber);
    else if(part=="link") cradle_link();
    else if(part=="links") for(y=[0,18]) translate([0,y,0]) cradle_link();
    else if(part=="heater_clamp") heater_clamp();
    else if(part=="heater_clamps") for(x=[0,21]) translate([x,0,0]) heater_clamp();
    else if(part=="fit") translate([vessel_xmax-body_width,rim_overhang,-body_height+12]) intersection() {
        vessel(0);
        translate([-vessel_xmax,-5,body_height-12]) cube([3*vessel_xmax,body_depth+10,13]);
    }
    else if(part=="assembly") assembly();
    else if(part=="exploded") assembly(explode=24);
    else if(part=="liquid") water();
    else if(part=="loaded_liquid") water(loaded_level,true);
    else if(part=="paper") paper();
    else if(part=="single_assembly") {
        color("SteelBlue") vessel(chamber);
        color("Goldenrod") translate([0,0,body_height]) guide(chamber);
        color("Orange") installed_clips();
    }
    else assert(false,"Unknown v2 part");
}
