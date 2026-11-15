// V1.8 deliberately shares the v2 wet geometry, without copying or scaling it.
include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v2/guide.scad>
include <base.scad>
part = "assembly";
chamber = 0;
valid() valid_base() {
    echo(base_mm=[base_width,base_depth,cradle_floor+socket_height],
         bath_ml=working_ml,slot_pitch_mm=vessel_pitch);
    if(part=="assembly") unheated_assembly();
    else if(part=="exploded") unheated_assembly(45);
    else if(part=="base") shared_base();
    else if(part=="vessel") vessel_print(chamber);
    else if(part=="guide") guide_print(chamber);
    else if(part=="cover") guide_print(chamber,closed=true);
    else if(part=="clips") for(x=[0,14]) for(y=[0,14]) translate([x,y,0]) clip_print();
    else if(part=="fit") translate([vessel_xmax-body_width,rim_overhang,-body_height+12]) intersection() {
        vessel(0);
        translate([-vessel_xmax,-5,body_height-12]) cube([3*vessel_xmax,body_depth+10,13]);
    }
    else assert(false,"Unknown v1.8 part");
}
