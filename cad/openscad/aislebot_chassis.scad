// AisleBot chassis replica — dimensioned, parametric.
//
// Built to replace the abstract "box + hatched rectangles" kinematics
// sketch with something that actually looks like the SolidWorks model
// (base plate + centre reinforcement bracket + 4 mecanum wheels) and
// carries the dimensions on the model itself.
//
// Every number below is tagged with where it came from:
//   CONFIRMED  — already in docs/Master_Reference.md §2.1/2.4, sourced
//                there from the SolidWorks/URDF model.
//   MEASURED   — pixel-measured off the SolidWorks screenshots you
//                posted, calibrated against the CONFIRMED 1000x250mm
//                plate and 152.4mm wheel OD (cross-checked to within
//                ~2%, see the three numbers below that came out
//                matching CONFIRMED values almost exactly: wheel
//                centres at l1=403/l2=333/d=157.7 and OD=152.4mm).
//   ESTIMATED  — a reasonable guess where neither of the above exists
//                (plate steel gauge, bracket standoff height). Change
//                these to match the real part before this goes in the
//                report as anything more than a layout diagram.
//
// This is not a byte-exact reconstruction of the .SLDASM — that would
// need SolidWorks/eDrawings to read the native file, which isn't
// available in the environment this was built in. It reproduces the
// shape and every dimension that could be confirmed or measured.

/* [Chassis — CONFIRMED, Master_Reference.md §2.1] */
chassis_length = 1000;   // mm, overall plate length
chassis_width  = 250;    // mm, overall plate width
l1 = 403;                // mm, outer-wheel (FR, RL) longitudinal offset from centre
l2 = 333;                // mm, inner-wheel (FL, RR) longitudinal offset from centre
d  = 157.69;             // mm, half track width (all wheels)

/* [Wheels — CONFIRMED, Master_Reference.md §2.4] */
wheel_od     = 152.4;    // mm, DekuPro 6" SR mecanum outer diameter
wheel_radius = wheel_od/2;
roller_count = 10;       // datasheet says 10-12 rollers at 45°

/* [Wheels — MEASURED off your screenshots] */
wheel_width  = 57;       // mm, axle-direction width (measured, not on any datasheet page here)

/* [Centre bracket — MEASURED off your screenshots] */
bracket_span_x     = 300;  // mm, overall length of the two crossbars (x: -150..+150)
bracket_bar_depth  = 23;   // mm, each crossbar's thickness along x
strut_offset_x     = 71;   // mm, the two connecting struts sit at x = ±71
strut_width_x      = 26;   // mm, each strut's width along x
bolt_hole_dia      = 6;    // mm, guessed fastener size for the 3 holes per crossbar — verify
bolt_hole_offsets  = [-106, 0, 106]; // mm, x-offsets of the 3 holes per crossbar, measured

/* [Plate/bracket thickness — ESTIMATED, not visible in a top/bottom orthographic view] */
plate_thickness   = 3;    // mm — typical laser-cut steel gauge, VERIFY against real part
bracket_thickness = 20;   // mm, bracket standoff height below the plate, VERIFY

/* [Unidentified component — MEASURED position only] */
// A small square component appears at this same spot in both your top and
// bottom screenshots. Position measured; identity not confirmed (could be
// an E-stop, a limit switch, a sensor mount — call it out before publishing).
misc_component_pos = [-431, -71];
misc_component_size = [12, 12, 10];

// ---------------------------------------------------------------------
// Geometry
// ---------------------------------------------------------------------

module base_plate() {
    color("SlateGray")
    linear_extrude(height = plate_thickness)
        square([chassis_length, chassis_width], center = true);
}

module crossbar(y_center) {
    difference() {
        translate([0, y_center, -bracket_thickness])
            linear_extrude(height = bracket_thickness)
                square([bracket_span_x, bracket_bar_depth], center = true);
        for (ox = bolt_hole_offsets)
            translate([ox, y_center, -bracket_thickness - 0.5])
                cylinder(d = bolt_hole_dia, h = bracket_thickness + 1, $fn = 24);
    }
}

module strut(x_center) {
    translate([x_center, 0, -bracket_thickness])
        linear_extrude(height = bracket_thickness)
            square([strut_width_x, chassis_width - 2*bracket_bar_depth], center = true);
}

module center_bracket() {
    color("Peru") {
        crossbar( (chassis_width/2) - bracket_bar_depth/2);
        crossbar(-(chassis_width/2) + bracket_bar_depth/2);
        strut( strut_offset_x);
        strut(-strut_offset_x);
    }
}

// A DekuPro-style mecanum wheel: hub + barrel rollers at 45 degrees.
// This reproduces the general shape (hub, roller count, angle, envelope
// diameter/width), not the DekuPro roller profile itself.
// Kept within the true wheel envelope (OD/width exact for dimensioning) —
// diagonal grooves are engraved into the surface to suggest the roller
// layout rather than modelled as separate roller solids, which produced
// spiky, non-representative geometry sticking outside the real envelope.
module mecanum_wheel(handedness = 1) {
    difference() {
        color("DimGray") cylinder(r = wheel_radius, h = wheel_width, center = true, $fn = 64);
        for (i = [0 : roller_count - 1]) {
            angle = i * 360 / roller_count;
            rotate([0, 0, angle])
                translate([wheel_radius, 0, 0])
                rotate([handedness * 45, 0, 0])
                color("Black") cube([6, wheel_radius * 0.5, wheel_width * 1.5], center = true);
        }
    }
    color("Black") cylinder(r = wheel_radius * 0.18, h = wheel_width + 1, center = true, $fn = 24);
}

// Wheel placement: axle along Y, wheel centre in the chassis XY plane,
// resting so its bottom just touches the plate's underside plane (z=0
// at plate bottom face here — offset up by plate_thickness/2 for display).
module wheel_at(x, y, handedness) {
    translate([x, y, plate_thickness/2])
        rotate([90, 0, 0])
        mecanum_wheel(handedness);
}

// ---------------------------------------------------------------------
// Dimension annotations — centre marks, centrelines, callouts
// ---------------------------------------------------------------------

module center_cross(size = 30, thickness = 1) {
    color("Red") {
        translate([-size/2, 0, plate_thickness + 0.5]) cube([size, thickness, 0.5]);
        translate([0, -size/2, plate_thickness + 0.5]) cube([thickness, size, 0.5]);
    }
}

module centerlines() {
    color("Red", 0.6) {
        translate([-chassis_length/2 - 20, -0.25, plate_thickness + 0.4])
            cube([chassis_length + 40, 0.5, 0.3]);
        translate([-0.25, -chassis_width/2 - 20, plate_thickness + 0.4])
            cube([0.5, chassis_width + 40, 0.3]);
    }
}

module label(txt, pos, size = 14, rot = 0) {
    color("Black")
    translate([pos[0], pos[1], plate_thickness + 0.6])
        rotate([0, 0, rot])
        linear_extrude(height = 0.4)
            text(txt, size = size, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

module dim_line(from, to, offset_txt, txt, size = 12) {
    color("Red")
    hull() {
        translate([from[0], from[1], plate_thickness + 0.5]) cylinder(r = 1.2, h = 0.3, $fn = 12);
        translate([to[0], to[1], plate_thickness + 0.5]) cylinder(r = 1.2, h = 0.3, $fn = 12);
    }
    mid = [(from[0]+to[0])/2 + offset_txt[0], (from[1]+to[1])/2 + offset_txt[1]];
    label(txt, mid, size);
}

module dimensions() {
    // Overall length / width, offset outside the footprint
    dim_line([-chassis_length/2, -chassis_width/2 - 40], [chassis_length/2, -chassis_width/2 - 40],
              [0, -15], str("L = ", chassis_length, " mm"));
    dim_line([chassis_length/2 + 40, -chassis_width/2], [chassis_length/2 + 40, chassis_width/2],
              [30, 0], str("W = ", chassis_width, " mm"));

    // Wheel-centre track dimensions (l1, l2, d) drawn on the footprint itself
    dim_line([0, 0], [l1, d], [20, 15], str("l1 = ", l1, " mm"), 10);
    dim_line([0, 0], [l2, -d], [20, -15], str("l2 = ", l2, " mm"), 10);
    dim_line([l1, d], [l1, -d], [35, 0], str("2d = ", 2*d, " mm"), 10);

    // Wheel diameter callout, next to one wheel
    label(str("wheel OD = ", wheel_od, " mm"), [l1, d + wheel_width/2 + 20], 9);

    // Centre + centrelines
    center_cross(40, 1.2);
    centerlines();
    label("(0,0) chassis centre", [40, 12], 8);
}

// ---------------------------------------------------------------------
// Assembly
// ---------------------------------------------------------------------

base_plate();
center_bracket();

// FR outer, RL outer, FL inner, RR inner — signs per docs/Master_Reference.md §7.2
wheel_at( l1,  d, 1);   // FR
wheel_at(-l1, -d, 1);   // RL
wheel_at( l2, -d, -1);  // FL
wheel_at(-l2,  d, -1);  // RR

// Unidentified small component, position only (see note above)
color("Yellow")
translate([misc_component_pos[0], misc_component_pos[1], plate_thickness])
    cube(misc_component_size, center = true);

dimensions();
