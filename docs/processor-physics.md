# Processor physics and PETG print audit

This study uses OpenFOAM v2606 finite-volume solvers for the native 16:9 bath,
with water as a proxy for chemistry. It is a predictive engineering model, not
measured performance of a printed vessel. The five-part v1.8 remains unheated;
the thermal cases add the proposed external v2 heater stack to its flat rear.

## What is modeled

**Filling:** three-dimensional `interFoam`, solving incompressible water/air
volume fraction, momentum and pressure with gravity, viscosity and surface
tension. An initially empty 122 × 14 × 200.33 mm cavity receives 323 ml through a
centered 12 × 6 mm downward jet over five seconds, then settles for two seconds.
A separate coarse run pours for ten seconds. The top is open; water can leave
through the atmospheric opening. Inlet/outlet phase fluxes and stored water are
recorded separately. This is computed fluid motion, unlike the earlier CAD
animation that simply raised a liquid surface.

The mesh target is 4, 2.5 or 2 mm; individual block subdivisions can be smaller.
These meshes do not resolve droplets or capillary-scale surface details. The
rounding, bottom paper stops and 0.4 mm fill ridge are omitted, as are bottle
shape, hand motion and calibrated wetting/contact angle. The laminar model
resolves motion on the mesh but is not a validated turbulence/splash model.
Do not infer a precise safe pour rate or spill amount from these runs.

**Heating:** three-dimensional transient `chtMultiRegionFoam`, coupling buoyant
laminar water flow to heat conduction through PETG, a compliant pad, aluminium
spreader and heater. The 3 mm PETG wall, 4 mm floor and liquid level follow the
16:9 design. Rectangularization gives 324.03 ml versus the CAD's 323 ml (+0.32%).
No paper/agitation is present. The liquid is already in place at time zero;
thermal exchange *during pouring* is not coupled to the VOF calculation.

The heater stack follows the earlier v2 proposal: 124 × 179 × 0.5 mm pad,
156 × 182 × 1.5 mm aluminium and a 140 × 150 × 3 mm heater, supplying a total
of 5 W (not 5 W per cell or per bath pair). It is an isolated chamber model;
base contact, straps, neighboring bath and actual heater internals are omitted.
Interface contact is perfect apart from the explicit pad's resistance.

| Material | Density kg/m³ | Heat capacity J/(kg K) | Conductivity W/(m K) |
| --- | ---: | ---: | ---: |
| Water | 998 | 4180 | 0.6 |
| PETG | 1270 | 1200 | 0.2 |
| Compliant pad | 1800 | 1000 | 1 |
| Aluminium | 2700 | 900 | 205 |
| Heater equivalent solid | 1400 | 1200 | 0.2 |

These are assumed constant engineering properties, not measurements of the
ordered components or filament. Water uses the Boussinesq density relation with
β = 0.0003/K and viscosity 0.0008 Pa s. Printed PETG is treated as isotropic,
fully dense material; porosity and directional layer bonding are not resolved.

Room temperature is 20°C. Exposed solids use convection h = 5 W/(m² K) and
surface radiation (emissivity 0.9, aluminium 0.15). The free surface uses an
effective h = 3 plus radiation to represent the headspace/slotted top; the
top's mass is omitted. Sensitivities use outside h = 3 and 8, and surface h = 30.
The last is an increased-loss bracket, **not an evaporation transport model**.
No humidity, vapor concentration or evaporated mass is calculated.

## Results and interpretation

The machine-readable results, temperature curves, conservation accounting and
movies are distributed with the dated artifact bundle. The report separates
coarse and refined fill predictions rather than averaging them into a result.

The model predicts that a 5 W pad slows cooling but cannot hold a 35–38°C bath
in a 20°C room with this exposed geometry. Starting with a cold vessel produces
a rapid initial drop as the walls and heater assembly warm up. Preheating the
whole assembly reduces that initial drop, but does not remove ongoing losses.
Starting from 20°C is slow: 5 W has to warm both liquid and assembly while
continually losing heat to the room. The liquid also develops vertical thermal
gradients; an average temperature alone does not establish processing uniformity.

For color-temperature operation, the next design should evaluate insulation,
heater power and closed-loop sensing together. The present study does not pick
a safe higher-power heater or certify PETG temperature limits. Measure the actual
pad power and use water tests with top/middle/bottom probes to calibrate losses
and gradients before relying on a temperature setpoint for chemistry.

## Numerical checks

The thermal baseline uses a nominal 6 mm x/z target and ≤2 mm through depth,
with conforming thinner solid layers. A 4 mm mesh and a halved time step are
compared over the first ten minutes. The initial hot-water/cold-wall transient
uses a 0.005 s starting step and eight outer coupling correctors for 30 seconds;
later steps are capped at 0.5 s with two correctors. This avoids the spurious
startup temperature overshoot found in the exploratory runs. Only the corrected
cases belong in the final results. The nominal liquid-temperature averages are
less sensitive to mesh/time step than the fill model's splash quantity.

Sensible-energy storage uses reference density × Cp × region volume × ΔT.
It is compared with supplied power and integrated external wall heat flux.
The residual includes the Boussinesq approximation and sampled flux quadrature;
it is reported explicitly, not silently forced to zero. A uniform 20°C,
heater-off case checks temperature drift. Filling is independently checked via
water volume in, volume out and volume retained; mixture mass flux is converted
to water volume flux using both phase densities. Restart records are joined by
physical time without double-counting duplicate samples.

## PETG features and nozzle checks

The one geometry change is increasing the end ledges from 11 to 12 mm. The
minimum plastic beside the top's magnet pockets grows from 0.8 to **1.3 mm**.
The 170.8 × 138 mm shared base and five-part count are unchanged. Updated top
width is 160.45 mm; vessel flange width is 152 mm. Both presets retain A1 mini fit.

| Feature | Nominal size | Interpretation |
| --- | --- | --- |
| Vessel wall / floor | 3 / 4 mm | Engraved vessel letters leave at least 2.4 mm wall |
| Base floor / socket wall | 4 / 3 mm | Base lettering leaves at least 3.4 mm floor |
| Locating rim | 1.2 mm thick × 1.5 mm high | Several bead widths with the 0.4 mm nozzle |
| Fill ridge | 0.4 mm projection × 0.6 mm height | Wall-backed bump, not a free-standing 0.4 mm wall |
| Magnet outer ligament | 1.3 mm minimum | Increased for handling strength |
| Pocket floors | 1.3 mm top / 1.8 mm vessel | Blind pockets remain dry |
| Pull tab / top | 4.5 mm thick | Engraved tab letter leaves 3.9 mm |
| Slot wiping land | 0.4 mm high | Two 0.20 mm or four 0.10 mm layers in the inverted top |
| Tactile bars / bottom stops | 2 mm wide / Ø4 mm | Connected to substantial material |
| Sacrificial bed rail | 0.4 mm high | Intentionally thin and removed after printing |

Tested in Bambu Studio 2.7.1.57 using its resolved **Generic PETG / A1 mini**
profiles, with four walls and 1.2 mm top/bottom shell thickness:

- 0.4 mm nozzle, 0.20 mm Standard: six top/bottom layers.
- 0.2 mm nozzle, 0.10 mm Standard: twelve top/bottom layers.
- Vessels: supplied 44.2° tilt, build-plate tree supports at 30°, 3 mm outer brim.
- Tops inverted; base flat; neither needs supports or brim. No auto-orientation.

All five 16:9 plates, both 2:1 vessels and the differently labeled 2:1 base slice
without warnings for both nozzles (16 plate/nozzle runs). The tops are identical
between presets.
Deposition probes cover the fill ridge's straights and rounded corners, rim
straights, slot land, magnet outer ligament and pocket floor: 100% of the sampled
points are within intended extrusion footprints at both nozzle sizes. This
uses reported bead width and layer height with 0.055 mm sampling tolerance;
it is not a global minimum-wall tomography or a physical bead-shape model.
FreeCAD independently re-imports both STEP sets and checks solid validity,
clearances, pocket floors, ridge continuity, rigid paper movement and bath removal.
FreeCAD and build123d share Open Cascade, so this is not an independent geometry kernel.

**0.4 mm is the practical first-print choice** based on these toolpaths. The
0.2 mm nozzle is usable but substantially slower. No slicer can establish
watertightness, rim durability, magnet/adhesive retention or chemical compatibility.
Inspect supports and make the first water/fit trial before using chemistry.

## Reproduce

Install OpenFOAM v2606 (native OpenFOAM.app on this Mac, or a sourced OpenFOAM
installation on Linux), Bambu Studio and the existing FreeCAD runtime.

```sh
uv pip install --python .venv-cad/bin/python -r simulation/physics/requirements.txt
.venv-cad/bin/python simulation/physics/run_thermal.py build/example-hot --hot 38 --power 5
.venv-cad/bin/python simulation/physics/run_thermal.py build/example-cold --hot 20 --power 5
.venv-cad/bin/python simulation/physics/fill.py build/example-fill --spacing 2.5 --pour-seconds 5
openfoam interFoam -case build/example-fill > build/example-fill/log.solver 2>&1
.venv-cad/bin/python simulation/physics/render.py fill build/example-fill build/example-videos
.venv-cad/bin/python scripts/check_native.py --output build/print-model
.venv-cad/bin/python scripts/check_native_print.py build/print-model/16x9 build/sliced-04 --nozzle .4
.venv-cad/bin/python simulation/physics/print_paths.py build/sliced-04
```

On a sourced Linux installation omit the `openfoam` launcher before solver names.
The run wrapper detects the launcher automatically. Use fresh output folders;
keep `0/`, `constant/`, `system/`, scenario JSON, logs and postProcessing data.
`analyze.py CASE_ROOT REPORT_FOLDER` expects the named suite in the dated bundle;
`render.py thermal CASE_ROOT REPORT_FOLDER` renders the three principal cases.
For parallel VOF runs, use `decomposePar`, `mpirun -np 4 interFoam -parallel`,
then `reconstructPar` before rendering. Full volumetric fields are large and
remain local; Git contains source and compact evidence, not multi-gigabyte runs.

References: [OpenFOAM solver descriptions](https://www.openfoam.com/documentation/user-guide/a-reference/a.1-standard-solvers),
[conjugate heat-transfer solver](https://doc.openfoam.com/2212/tools/processing/solvers/rtm/heat-transfer/chtMultiRegionFoam/),
[native OpenFOAM.app](https://github.com/gerlero/openfoam-app),
[IAPWS water-property releases](https://www.iapws.org/release.html).
Actual numerical schemes and boundary dictionaries are saved with each case;
water constants here are approximations rather than a full IAPWS implementation.
