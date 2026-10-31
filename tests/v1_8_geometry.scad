include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v2/guide.scad>
include <../v1_8/base.scad>
check="base";
chamber=0;
// Conservative continuous swept envelopes, lifted off the intentional seating plane.
// Only the bottom segment can cross the socket during upward removal. Clipping
// before taking its hull avoids projecting the high filling well into the socket.
module removal_path(id,lower_only=false) {
    hull() for(lift=[0.01,body_height]) module_position(id) vessel_position(id,lift) {
        if(lower_only) intersection() {
            vessel(id);
            translate([-vessel_xmax,-5,-eps]) cube([3*vessel_xmax,body_depth+10,socket_height+2*eps]);
        }
        else vessel(id);
    }
}
valid() valid_base() {
    if(check=="base") shared_base();
    else if(check=="removal") intersection() { shared_base(); removal_path(chamber,true); }
    else if(check=="neighbor") intersection() {
        removal_path(chamber);
        module_position(1-chamber) vessel_position(1-chamber) {
            vessel(1-chamber);
            translate([0,0,body_height]) guide(1-chamber);
            installed_clips();
        }
    }
    else assert(false,"Unknown v1.8 probe");
}
