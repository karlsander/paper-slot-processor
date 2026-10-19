// Snap the C-shaped collar onto the arms from the side, near the handle.
// Slide toward the jaws to grip; park near the handle to release.
include <lib/parameters.scad>
include <lib/tong.scad>
show = "plate"; // [plate,assembled,tong,collar]
validate_parameters() {
    if (show == "plate") tong_plate();
    else if (show == "assembled") { tong(); parked_collar(); }
    else if (show == "tong") tong();
    else if (show == "collar") collar();
    else assert(false, "show must be plate, assembled, tong or collar.");
}
