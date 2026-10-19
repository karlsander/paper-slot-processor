// One continuous loft from the visible fill bowl into the chamber.
// Every horizontal section is round. The bend eases from vertical to a 45°
// descending bore, keeping the inside roof printable without trapped supports.
function smoothstep(t) = t * t * (3 - 2 * t);
function inlet_run(drop) = drop < inlet_bend_height ?
    drop * drop / (2 * inlet_bend_height) : drop - inlet_bend_height / 2;
function inlet_station(z) = z <= pool_z ?
    [z, -inlet_offset + inlet_run(pool_z - z), inlet_bore_diameter / 2] :
    [z, -inlet_offset, inlet_bore_diameter / 2 +
        (inlet_opening_diameter - inlet_bore_diameter) / 2 *
        smoothstep(min(1, (z - pool_z) / inlet_funnel_height))];
// Shared stations make the volume integral follow the actual faceted loft.
inlet_stations = concat(
    [for (i = [0 : inlet_path_steps]) inlet_station(inlet_exit_z +
        (pool_z - inlet_exit_z) * i / inlet_path_steps)],
    [for (i = [1 : inlet_funnel_steps]) inlet_station(pool_z +
        inlet_funnel_height * i / inlet_funnel_steps)],
    [[inlet_top_z, -inlet_offset, inlet_opening_diameter / 2]]);
function inlet_section(z, i = 0) =
    z <= inlet_stations[0][0] ? [inlet_stations[0][1], inlet_stations[0][2]] :
    i >= len(inlet_stations) - 2 || z <= inlet_stations[i + 1][0] ?
        let(a = inlet_stations[i], b = inlet_stations[i + 1],
            t = min(1, max(0, (z - a[0]) / (b[0] - a[0]))))
        [a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])] :
    inlet_section(z, i + 1);
function inlet_shell(z) = inlet_wall + (inlet_wall_top - inlet_wall) *
    smoothstep(min(1, max(0, (z - pool_z) / inlet_funnel_height)));

module inlet_loft(shell = false) {
    n = $fn;
    points = [for (s = inlet_stations) for (j = [0 : n - 1])
        let(r = s[2] + (shell ? inlet_shell(s[0]) : 0), a = j * 360 / n)
        [r * cos(a), s[1] + r * sin(a), s[0] + (!shell && s[0] == inlet_top_z ? eps : 0)]];
    // OpenSCAD polyhedron faces use clockwise order viewed from outside.
    faces = concat([[for (j = [0 : n - 1]) j]],
        [for (i = [0 : len(inlet_stations) - 2]) for (j = [0 : n - 1])
            [i * n + j, (i + 1) * n + j,
                (i + 1) * n + (j + 1) % n, i * n + (j + 1) % n]],
        [[for (j = [n - 1 : -1 : 0]) (len(inlet_stations) - 1) * n + j]]);
    // End fully inside the bath, never cut into the opposite wall/divider.
    intersection() {
        polyhedron(points, faces, convexity = 10);
        translate([-inlet_opening_diameter, -inlet_offset - inlet_outer_radius - 1, inlet_exit_z - 1])
            cube([2 * inlet_opening_diameter,
                inlet_offset + inlet_outer_radius + 1 + wall_thickness + min(2, slot_gap / 2),
                inlet_top_z - inlet_exit_z + 2]);
    }
}
