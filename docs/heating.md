# Heating each chamber independently

The October 2026 physics study predicts that the original 5 W mat reaches only
about **26.5°C equilibrium in a 20°C room**. Hot filling saves warm-up time but
does not change equilibrium. For 35°C, the revised model needs roughly 11 W per
bath nominally, or 14.6 W under the higher-air-loss assumption.

A practical first candidate is **RS PRO 731-350: 12 V DC, 15 W,
100 × 150 × 1.4 mm**, one per bath, on an external aluminium spreader.
See the [official datasheet](https://docs.rs-online.com/ba83/A700000008849926.pdf)
and [German product listing](https://de.rs-online.com/web/p/heizmatten/0731350).
Use independent liquid-temperature feedback and heater overtemperature protection.
At full power the predicted nominal equilibrium is 40.1°C, so power control is
necessary for a 35°C setpoint. 15 W has little reserve in a draft; approximately
20 W with control would be a better design target for robust higher-loss use,
but a fitting 20 W product has not been selected.

The five-part v1.8 is unheated. Its 180 mm tapered base and 25 mm chamber gap
require a new heater mount; the original v2 hardware is not a drop-in assembly.
The thermal study omits the base and neighboring bath. Mounting height, lead exit,
contact quality and actual water temperatures must be checked on the heated prototype.
Full assumptions, scenarios and numerical checks are in [the physics report](processor-physics.md).

## Earlier 5 W concept (historical)

The following describes the original v2 envelope, not the new recommendation.

Use a separate flat **140 × 150 mm, 5 W mat** and metal spreader behind each approximately 325 ml bath. The plates remain separate so one bath does not deliberately share its heater with another. This version is built for the small 5 W modules; evaluate them with water before redesigning for a different heater.

The user supplied the [INVITAL 140 × 150 mm, 5 W listing](https://www.invital.de/invital-heizmatte-14-x-15-cm-5-w). The listing was read on 20 October 2026. It describes manual power adjustment and requires at least 1 cm of ventilation when installed between objects. Its support answer specifies **glass terrariums only** and does not guarantee use on plastic. This CAD envelope therefore does not approve this mat for a printed liquid vessel, including through a metal plate. Product-specific compatibility and actual connection clearance remain unresolved. The separate Amazon link (ASIN B0GY3BLXNF) was not independently verified.

**5 W is a modest experimental starting point, not a promise of maintaining 35–38°C.** Mix with water already around 35–38°C, let the baths settle, gently mix and measure each one, then use the user's previously tested temperature/time workflow. Prewarming removes most of the initial heating delay but does not change equilibrium temperature.

For scale, 5 W could warm 325 ml of water by about **0.22°C per minute with no losses**. Real heat transfer is lower and losses grow as the bath gets warmer than the room. `scripts/thermal_v2.py` is an uncalibrated sensitivity calculation with explicit assumptions; it must not be read as a measured temperature prediction or product certification.

There is no thermostat or permanent probe in this build. Each manual dial adjusts power, not a temperature setpoint. Independent settings can produce different bath temperatures, with some remaining coupling through nearby air and the printed base links. A fever thermometer must display the actual equilibrium temperature, which may be below its measurement range. Keep any thermometer used for chemistry dedicated to that purpose.

Keep the mat flat, its rear air gap ventilated, and its connection clear of the loose edge keepers. Do not enclose it in insulation. The plate supports the complete mat. The cable restraint is adjustable by placement and ties; it is not a molded fit to a particular connection. Keep electrical connections dry, provide a drip loop, and disconnect before cleaning or changing a cassette. The metal stays outside the chemistry.

No heater has been purchased or physically tested. Physical water tightness, wet-paper handling, contact quality, thermal gradients and equilibrium temperature remain to be measured. The old shared 20 W holder is superseded by these independent modules.
