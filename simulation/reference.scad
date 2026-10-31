// Thin fit-critical sections avoid intentionally omitted lettering and floor stops.
include <../v2/parameters.scad>
include <../v2/geometry.scad>
include <../v2/vessel.scad>
include <../v1_8/base.scad>
part="base";
valid() valid_base() intersection() {
    if(part=="base") shared_base(); else vessel(0);
    translate([-100,-100,20]) cube([500,500,1]);
}
