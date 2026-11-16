// Interlocked HV test enclosure for the charger (flat-pack acrylic/PC hood + printed/phenolic base).
// NOT YET RENDERED OR MEASURED - charger_* values are estimates from a photo. Measure the real
// charger and edit the PARAMETERS block, then export parts:  openscad -D 'part="bom"' ...
// part = "assembly" | "base" | "hood" | "bom"

part = "assembly";

// ---------- PARAMETERS (mm) ----------
charger_l = 250;  charger_w = 150;  charger_h = 90;   // ASSUMED: housing incl. mounting flange
hv_clearance = 50;     // min air gap from charger / HV clips to any conductive part or hood wall
top_clearance = 60;    // headroom for leads + alligator clips
panel_t = 6;           // clear polycarbonate (preferred) or acrylic; non-conductive
base_t = 10;           // FR4 / phenolic / HDPE sheet; do NOT use metal or plywood
lead_hole_d = 22;      // input cord + output lead pass-through (back panel, grommeted)
switch_w = 28; switch_h = 16;  // safety interlock microswitch pocket (lid side)
mat_l = 600; mat_w = 450;      // insulating mat under whole fixture (see docs/03)

in_l = charger_l + 2*hv_clearance;
in_w = charger_w + 2*hv_clearance;
in_h = charger_h + top_clearance;
base_l = in_l + 2*panel_t + 40;  base_w = in_w + 2*panel_t + 40;

module base() {
  difference() {
    cube([base_l, base_w, base_t]);
    // charger location marks (shallow 1 mm engraving) + cable relief
    translate([(base_l-charger_l)/2, (base_w-charger_w)/2, base_t-1]) cube([charger_l, charger_w, 2]);
    for (x=[20, base_l-20], y=[20, base_w-20]) translate([x,y,-1]) cylinder(d=5, h=base_t+2, $fn=24); // M5 mat studs
  }
}

module panel(sz) cube(sz);

module hood() {
  ox = (base_l-in_l)/2 - panel_t;  oy = (base_w-in_w)/2 - panel_t;
  translate([ox, oy, base_t]) {
    // back (cable) panel with two grommet holes
    difference() { translate([0, in_w+panel_t, 0]) panel([in_l+2*panel_t, panel_t, in_h]);
      for (x=[in_l*0.3, in_l*0.7]) translate([x+panel_t, in_w+panel_t-1, in_h*0.25]) rotate([-90,0,0]) cylinder(d=lead_hole_d, h=panel_t+2, $fn=32); }
    panel([panel_t, in_w+panel_t, in_h]);                              // left
    translate([in_l+panel_t, 0, 0]) panel([panel_t, in_w+panel_t, in_h]); // right
    translate([0, 0, in_h]) panel([in_l+2*panel_t, in_w+2*panel_t, panel_t]); // top
    // front door (hinged at top; opening it must open the interlock switch)
    color("lightblue", 0.4) translate([panel_t, -panel_t, 0]) panel([in_l, panel_t, in_h]);
  }
}

module bom() {
  echo(str("BASE  : ", base_l, " x ", base_w, " x ", base_t, " mm  qty 1"));
  echo(str("BACK  : ", in_l+2*panel_t, " x ", in_h, " x ", panel_t, " mm  qty 1 (2x D", lead_hole_d, " holes)"));
  echo(str("SIDES : ", in_w+panel_t, " x ", in_h, " x ", panel_t, " mm  qty 2"));
  echo(str("TOP   : ", in_l+2*panel_t, " x ", in_w+2*panel_t, " x ", panel_t, " mm  qty 1"));
  echo(str("DOOR  : ", in_l, " x ", in_h, " x ", panel_t, " mm  qty 1 (hinge top, + switch pocket ", switch_w, "x", switch_h, ")"));
  echo(str("MAT   : ", mat_l, " x ", mat_w, " mm insulating mat"));
}

if (part == "base") base();
else if (part == "hood") hood();
else if (part == "bom") bom();
else {
  color("dimgray") base();
  hood();
  // charger placeholder
  color("slategray") translate([(base_l-charger_l)/2, (base_w-charger_w)/2, base_t]) cube([charger_l, charger_w, charger_h]);
}
