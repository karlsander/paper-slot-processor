// Assembly preview only. Printable plates are in plates/.
include <parts.scad>
format = "16:9"; // [16:9,4:3]
cover_count = 0; // [0:4]
exploded = 0; // [0:40]
check_parameters() assembly(format, cover_count, exploded);
