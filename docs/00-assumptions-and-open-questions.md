# Assumptions and open questions

## What I read from the photos
- **Tester**: Nanjing Changchuang **CC2670P** 耐电压测试仪 (withstand-voltage tester). Front panel: mA range switch
  (2 mA / "20 mA"), timer on/off, test/reset buttons, HV output socket with red lead, return lead, and a round
  multi-pin connector (probably the remote-control / interlock input, **verify in the manual before wiring**).
- **Charger (DUT)**: grey die-cast housing, open-top in the photo, EMI filter (toroids, X/Y caps) visible, mains
  input cord with a 3-pin plug with earth pin (so **Class I**), output cord with blue/black-ish leads on alligator clips.
- **Accessories**: HV probe (red, pointed tip), black return lead with alligator clip, green rubber mats.

## Assumptions (please confirm or correct)
1. The test you want is dielectric withstand with leakage trip, because the CC2670P cannot measure MΩ.
2. Test points: (a) L+N shorted to earth/case, (b) L+N shorted to the DC output.
3. Placeholder levels 1.5 kV and 3.0 kV AC, 2 s, 5 mA trip. These are NOT from your standard.
4. The charger housing is about 250 × 150 × 90 mm (estimate from the photo).

## Open questions
1. Which standard and which levels apply to this charger (IEC 62368-1, IS 13252, an EV-charger standard, customer spec)?
   Is the output SELV / isolated, and does the metal case connect to earth?
2. True IR in MΩ needed as well? If yes, which megohmmeter (and does it have RS-232/USB)?
3. Does your CC2670P have an RS-232 port or only the remote connector? (Decides whether the GUI can start the test and
   read leakage automatically, or stay in manual-entry mode.)
4. Cycle-time target (seconds per charger) and daily volume? Drives 1-2 s vs 60 s dwell and the fixture design.
5. What is the exact charger size and connector type, and are there other charger variants?
6. Rating/datasheet of the existing green mats?
7. Who signs off the safety review of the enclosure interlock?
