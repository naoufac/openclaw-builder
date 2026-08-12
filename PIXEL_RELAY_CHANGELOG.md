# Pixel Relay / Croissant Nation Changelog

## 2026-08-12 — v2.1 placeholder sprites + victory/combo UI
- Added `bakePlaceholderSprites()` to generate in-browser 16×16 pixel-art sheets for every `SPRITE_SOCKETS` entry (runnerA, runnerB, platform, orb, handoffZone, crescent, hazard, goal, baton, hearthGlow, 32×16 ghostTrail strip).
- Filled sprite hooks with image-based drawing + canvas fallback so the game renders immediately while Hardy works on final art.
- Added `comboChain` log tracking every crescent catch and hearth rekindle.
- Redesigned victory overlay as a stat panel with Score, Best, Pearls, Hearth Rekindled, Care Bonus, Crumb Crown multiplier, Perfect Run, and a visual Crumb Combo Chain.

## 2026-08-11 — v2.6-prep text-first seam
- Added 72 BPM tempo cue pulsing at the handoff arch.
- Added ghost route overlay showing intended relay path (oven → arch → crown).
- Added warmed-by provenance: baton warmth timer tracks continuous carry time; resets on spike hit and at handoff boundary.
- Formalized CARE BONUS return: returning Baker B through the arch after a clean handoff grants 100 + up to 50 provenance bonus.
- HUD expanded: Baker A/B status, tempo, time, best, seams, warmth, care bonus.
- Kept all sprite hooks (`drawRunner`, `drawPlatform`, `drawOrb`, `drawHandoffZone`, `drawCrescent`, `drawHazard`, `drawGoal`) unchanged for Hardy sprite pass.
