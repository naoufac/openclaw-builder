# Pixel Relay / Croissant Nation Changelog

## 2026-08-18 — sprite-socket drop guard
- `loadSpriteSheet` now validates every sheet before it may occupy a socket: frame dims (≥ frameW×frameH, width a multiple of frameW) and ≥ 8 visible pixels — rejects blank or mis-sized files that decode fine but render as nothing.
- Rejected URLs are cached per page-load (no per-frame refetch churn); network errors still retry.
- Sheets load with `crossOrigin='anonymous'` (GitHub Pages sends `ACAO: *`) so validation can read pixels; unreadable (tainted) canvases fall back to trust-as-before.
- Verified in headless Chromium: real art renders 100% pixel-identical to live (3800/3800 sampled band); blank 16×16 and 8×8 mis-sized drops are rejected and the baked placeholders take over.

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
