# Test procedure and safety

> HV test equipment can kill. The CC2670P label says: wear insulating gloves and work on an insulating mat.
> This document is a design draft, not a certified procedure. Have it reviewed by a qualified person.

## Connection (per test step)

```
 CC2670P HV out (red) ───────────────┐
                                      ├─ step 1: L+N shorted post  (return -> earth/case post)
 CC2670P return (black) ──────────────┘  step 2: L+N shorted post  (return -> both output leads clipped together)

 Fixture socket: 3-pin socket with L and N bridged inside. Charger plug sits in it.
```

| Step | HV lead to | Return lead to | Default V | Time | Trip |
|---|---|---|---|---|---|
| LN_PE | L+N (bridged socket post) | earth pin post / metal case | 1500 V AC | 2 s | 5 mA |
| LN_OUT | L+N (bridged socket post) | both DC output leads together | 3000 V AC | 2 s | 5 mA |

Set the CC2670P trip-current switch to match the recipe (2 mA or 20 mA range, then the current-preset knob).
The GUI's limit is a second, software check on the reading; the instrument's own trip is the real protection.

## Operator flow
1. Mat in place, gloves on, charger inside the enclosure on the base plate, lid open.
2. GUI: enter serial, operator, pick the recipe, Start.
3. Make the connections shown for the step. Close the lid (interlock lamp lit).
4. Tick "lid closed", set voltage on the CC2670P, press START, wait for the timer.
5. Type the leakage reading into the GUI (tick Breakdown if the alarm tripped). Press RESET on the tester.
6. The GUI forces the lid-confirm to reset after each step. Open the lid, change connections, repeat.
7. First failing step stops the test and records FAIL. Quarantine the unit.

## Safety rules the design enforces or assumes
- HV never applied with the lid open: the **hardware** interlock (microswitch in the tester's remote/enable circuit, or in series with HV enable) is the real protection. The GUI checkbox is only a procedural prompt.
- Minimum 50 mm air gap between HV points and any conductive part or the operator (hood walls).
- After each step, press RESET and wait before touching leads. The EMI-filter capacitors can hold charge.
- Never test an open-case charger outside the enclosure (the photo shows one with the cover off: fine for bring-up, not for production).
- Keep the CC2670P earthed. Use a dedicated earthed outlet.
