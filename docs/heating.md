# Heating one chamber at a time

Use a separate flat **140 × 150 mm, 5 W mat** and metal spreader behind each approximately 325 ml bath. The plates remain separate so one bath does not deliberately share its heater with another. This version is built for the small 5 W modules; evaluate them with water before redesigning for a different heater.

The user supplied the [INVITAL 140 × 150 mm, 5 W listing](https://www.invital.de/invital-heizmatte-14-x-15-cm-5-w). The listing was read on 20 October 2026. It describes manual power adjustment and requires at least 1 cm of ventilation when installed between objects. Its support answer specifies **glass terrariums only** and does not guarantee use on plastic. This CAD envelope therefore does not approve this mat for a printed liquid vessel, including through a metal plate. Product-specific compatibility and actual connection clearance remain unresolved. The separate Amazon link (ASIN B0GY3BLXNF) was not independently verified.

**5 W is a modest experimental starting point, not a promise of maintaining 35–38°C.** Mix with water already around 35–38°C, let the baths settle, gently mix and measure each one, then use the user's previously tested temperature/time workflow. Prewarming removes most of the initial heating delay but does not change equilibrium temperature.

For scale, 5 W could warm 325 ml of water by about **0.22°C per minute with no losses**. Real heat transfer is lower and losses grow as the bath gets warmer than the room. `scripts/thermal_v2.py` is an uncalibrated sensitivity calculation with explicit assumptions; it must not be read as a measured temperature prediction or product certification.

There is no thermostat or permanent probe in this build. Each manual dial adjusts power, not a temperature setpoint. Independent settings can produce different bath temperatures, with some remaining coupling through nearby air and the printed base links. A fever thermometer must display the actual equilibrium temperature, which may be below its measurement range. Keep any thermometer used for chemistry dedicated to that purpose.

Keep the mat flat, its rear air gap ventilated, and its connection clear of the loose edge keepers. Do not enclose it in insulation. The plate supports the complete mat. The cable restraint is adjustable by placement and ties; it is not a molded fit to a particular connection. Keep electrical connections dry, provide a drip loop, and disconnect before cleaning or changing a cassette. The metal stays outside the chemistry.

No heater has been purchased or physically tested. Physical water tightness, wet-paper handling, contact quality, thermal gradients and equilibrium temperature remain to be measured. The old shared 20 W holder is superseded by these independent modules.
