// Migration oracle only. Text metrics differ; retain tactile and fill marks.
include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v2/guide.scad>
include <../v1_8/base.scad>
module text(text, size, halign, valign, font) {}
part="base";
chamber=0;
closed=false;
valid() valid_base() {
    if(part=="base") shared_base();
    else if(part=="vessel") vessel(chamber);
    else if(part=="guide") guide(chamber,closed=closed);
    else if(part=="clip") retaining_clip();
    else if(part=="fit") translate([vessel_xmax-body_width,rim_overhang,-body_height+12]) intersection() {
        vessel(0);
        translate([-vessel_xmax,-5,body_height-12]) cube([3*vessel_xmax,body_depth+10,13]);
    }
}
