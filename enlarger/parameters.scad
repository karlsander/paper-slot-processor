// Millimetres. Rebuild every mating part after changing these settings.
paper_width = 102;
paper_thickness = 0.30; // Measure an unexposed offcut; not a Fuji specification.
paper_side_clearance = 0.30;
guide_height = 0.20; // Below the emulsion plane: no lip over the long edges.
deck_thickness = 4;
end_allowance = 20;
side_shelf = 14;
outer_rail_width = 4;
outer_rail_height = 1.6;
mask_thickness = 4.8;
mask_edge_land = 0.8;
mask_bevel = 3.2;
mask_side_clearance = 0.4;
magnet_diameter = 6;
magnet_thickness = 3;
magnet_diameter_clearance = 0.3; // Diametral; glue fit, not a press fit.
magnet_depth_clearance = 0.2;
locator_diameter = 3.2;
locator_height = 2;
locator_clearance = 0.5; // Diametral.
cover_thickness = 3;
cover_pin_diameter = 2.8;
cover_pin_height = 2.2;
cover_pin_clearance = 0.6; // Diametral.
cover_lap = 0.8;
cover_lap_height = 1;
cover_clearance = 0.2;
joint_clearance = 0.2;
joint_depth = 8;
build_size = [180, 180, 180];
bed_margin = 3;
$fn = 48;
eps = 0.01;

image_169 = paper_width * 16 / 9;
image_43 = paper_width * 4 / 3;
base_length = image_169 + 2 * end_allowance;
channel_width = paper_width + 2 * paper_side_clearance;
base_width = channel_width + 2 * side_shelf;
rail_inner = base_width / 2 - outer_rail_width;
mask_width = 2 * (rail_inner - mask_side_clearance);
paper_z = deck_thickness + paper_thickness;
mask_top = paper_z + mask_thickness;
magnet_x = base_length / 2 - 14;
locator_x = base_length / 2 - 4;
attachment_y = channel_width / 2 + 5.1;
cover_pin_x = base_length / 2 - 10;
cover_end = base_length / 2 - 3;
band_width = paper_width / 5;
cover_lap_gap = 0.2;

function image_length(format) = format == "16:9" ? image_169 : image_43;
function band_center(i) = -paper_width / 2 + (i + 0.5) * band_width;

module check_parameters() {
    assert(paper_width >= 80 && paper_width <= 105, "Supported paper width: 80 to 105 mm.");
    assert(paper_thickness >= 0.25 && paper_thickness <= 0.6, "Measure paper thickness (0.25 to 0.6 mm).");
    assert(guide_height > 0 && guide_height <= paper_thickness - 0.05,
        "Channel guides must remain below the emulsion surface.");
    assert(paper_side_clearance >= 0.15 && paper_side_clearance <= 0.6);
    assert(deck_thickness >= magnet_thickness + magnet_depth_clearance + 0.8);
    assert(mask_thickness >= magnet_thickness + magnet_depth_clearance + 1.4);
    assert(end_allowance >= 20 && end_allowance <= 23);
    assert(mask_edge_land >= 0.8 && mask_bevel <= mask_thickness - mask_edge_land);
    assert(mask_side_clearance >= 0.25 && mask_side_clearance <= 0.6);
    assert(magnet_diameter == 6 && magnet_thickness == 3, "Attachment layout is for 6 x 3 mm magnets.");
    assert(magnet_diameter_clearance >= 0.1 && magnet_diameter_clearance <= 0.5);
    assert(magnet_depth_clearance >= 0.1 && magnet_depth_clearance <= 0.3);
    assert(mask_width / 2 - attachment_y - (magnet_diameter + magnet_diameter_clearance) / 2 >= 1.2);
    assert(locator_height + 0.3 < mask_thickness && locator_clearance >= 0.3);
    assert(cover_thickness >= 2.8 && cover_thickness <= 4);
    assert(cover_pin_height < cover_thickness && cover_pin_clearance >= 0.4);
    assert(cover_lap >= 0.6 && cover_lap <= 1);
    assert(cover_lap_height >= 0.8 && cover_lap_height + cover_lap_gap < cover_thickness);
    assert(cover_clearance >= 0.15 && cover_clearance <= 0.3);
    assert(joint_clearance >= 0.15 && joint_clearance <= 0.35);
    assert(base_length / 2 + joint_depth <= build_size[0] - 2 * bed_margin);
    assert(base_width <= build_size[1] - 2 * bed_margin);
    assert((2 * cover_end + band_width + 2 * cover_lap) / sqrt(2)
        <= min(build_size[0], build_size[1]) - 2 * bed_margin, "Diagonal cover exceeds bed.");
    children();
}
