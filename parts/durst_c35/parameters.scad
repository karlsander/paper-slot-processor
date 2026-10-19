// Durst C35 carrier V0.1 — millimetres. See docs/durst-c35/README.md.
// CONFIRMED describes the user's observations, not a caliper certification.
// MEASURE / GUESS values are deliberately editable for the first fit print.
$fn = 64;
c35_eps = 0.02;

// X runs along the 36 mm window; Y runs from the rear/hinge towards the front.
// A's film-contact face is Z=0. B's face is Z=film_gap when closed.
window_x = 36;                      // CONFIRMED: A's clear opening.
window_y = 24;                      // CONFIRMED.
film_width = 35;                    // Nominal strip width, centred on window.
body_width = 94.6;                  // MEASURE: user reports >94 and <95.
b_rear_margin = 42;                 // User measurement, nominal window to plate end.
a_rear_margin = 32;                 // User measurement; A plate ends 10 mm sooner.
front_margin = 34;                  // GUESS: window to front face, both halves.
front_lip = 4;                      // GUESS: A only, beyond common front face.
lip_thickness = 2;
body_corner_radius = 2.5;
outer_height_a = 13.5;              // MEASURE: film face to outer skirt bottom.
outer_height_b = 13.5;              // MEASURE: excludes projecting hinge ears.
plate_thickness_a = 2.5;            // MEASURE: slot-critical section.
plate_thickness_b = 2.5;            // MEASURE: maximum, including outer window rim.
skirt_wall = 2;                     // GUESS.

// This is the ENTIRE space for the film, not clearance added to film thickness.
film_gap = 0.20;                    // FIT: controlled by hinge axis and four stops.
aperture_land = 0.4;                // Flat, exact-size edge at the film face.
aperture_flare = 1.2;               // GUESS: exterior bevel per edge.
b_aperture_relief = 0.8;            // GUESS: widening between B's four corner insets.
b_corner_inset_length = 1.8;        // GUESS: extent along each nominal corner.
b_outer_recess = 0.6;               // GUESS: outer panel below the window rim.
front_groove_depth = 0.35;           // GUESS: shallow groove away from film path.

film_pin_spacing = 58;              // CONFIRMED: centre-to-centre.
film_pin_diameter = 1.6;            // GUESS: nearest surface is on 35 mm strip edge.
film_pin_height = 1.2;              // GUESS.
film_pin_tip_height = 0.35;
b_pin_recess_mouth = 6;             // GUESS: broad, blind countersink.
b_pin_recess_bottom = 2.6;
b_pin_recess_depth = 1.3;            // Leaves 0.6 mm behind the recessed outer panel.

hinge_ear_height = 10;               // MEASURE: B ear, from its film face.
hinge_ear_width = 7;                 // MEASURE: front-to-rear extent.
hinge_hole_from_root = 7;            // MEASURE: centre is 3 mm above free tip.
hinge_ear_thickness = 1.8;           // GUESS: across X.
hinge_side_clearance = 0.35;         // FIT: B ear outside to A support inside.
hinge_pin_diameter = 2.4;            // GUESS.
hinge_hole_diameter = 2.9;           // FIT: 0.50 mm diametral clearance.
hinge_tip_engagement = 0.35;         // Pin extends beyond ear's inside face.
hinge_pin_tip_length = 0.4;

window_center_y = b_rear_margin + window_y / 2;
body_front_y = b_rear_margin + window_y + front_margin;
a_plate_rear_y = b_rear_margin - a_rear_margin;
hinge_y = -hinge_ear_width / 2;
hinge_z = film_gap - hinge_hole_from_root;
skirt_inner_x = body_width / 2 - skirt_wall;
ear_outer_x = skirt_inner_x - hinge_side_clearance;
ear_inner_x = ear_outer_x - hinge_ear_thickness;
hinge_pin_length = hinge_side_clearance + hinge_ear_thickness + hinge_tip_engagement;
film_pin_y = window_center_y - film_width / 2 - film_pin_diameter / 2;

assert(body_width > film_pin_spacing + film_pin_diameter + 2 * skirt_wall);
assert(a_plate_rear_y > 0 && a_plate_rear_y < b_rear_margin);
assert(front_margin > 15 && front_lip > 0);
assert(plate_thickness_a > aperture_land && plate_thickness_b > aperture_land);
assert(b_outer_recess >= 0 && b_outer_recess < plate_thickness_b - 1);
assert(film_gap > 0 && film_gap <= 0.8, "Use a small positive total film space.");
assert(film_pin_height > film_gap && film_pin_height - film_gap < b_pin_recess_depth);
assert(b_pin_recess_depth < plate_thickness_b - b_outer_recess);
assert(b_pin_recess_bottom > film_pin_diameter);
assert(b_aperture_relief >= 0 && b_corner_inset_length > 0);
assert(b_corner_inset_length < min(window_x, window_y) / 2);
assert(hinge_hole_diameter > hinge_pin_diameter);
assert(hinge_hole_from_root > hinge_hole_diameter / 2);
assert(hinge_ear_height - hinge_hole_from_root > hinge_hole_diameter / 2 + 0.6);
assert(hinge_ear_width > hinge_hole_diameter + 2);
assert(hinge_ear_thickness > 0 && hinge_side_clearance > 0);
assert(hinge_pin_length > hinge_pin_tip_length);
assert(hinge_hole_from_root + hinge_hole_diameter / 2 < outer_height_a);
