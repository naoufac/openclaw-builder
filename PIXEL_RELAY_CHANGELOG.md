# Pixel Relay / Croissant Nation Changelog

## 2026-08-18 — relay-chain hotfix: handoff reachable, crash killed, spawn fixed
Three compounding defects, all found by driving the real game with a scripted keyboard in headless Chromium:

1. **Solo control guard made the relay impossible.** Every update frame forced control back to the baton carrier unless BOTH bakers already stood inside the handoff arch — but Baker B spawns far away and could never be walked there, so the H handoff (and everything behind it: crescent, care bonus, hearth rekindle, crumb crown) was unreachable. The help panel's promise ("Use Space to switch control between bakers") was false. Fix: guard removed; Space now freely switches bakers, and `tryToggleRunner` still refuses toggling while both stand in the arch so the H handoff stays deliberate. Verified: pristine build holds Baker B pinned (cluster x=644 → 644 after 3 s of input); fixed build lets B walk the full route.
2. **`playCivicSeamBeat()` was never defined.** As soon as a handoff DID succeed, the civic seam activated (arch proximity + baked crumb trail) and the next 72 BPM beat boundary threw `ReferenceError` inside `update()` — the rAF loop died and the game froze ~200 ms after every handoff. Dormant only because defect 1 made handoffs impossible. Fix: call site is now a no-op; the seam pulse stays visual.
3. **Baker A spawned sunk 24 px into the start shelf** (`y=300` = shelf top, not standing height), got shoved sideways out of it, and fell to the floor — where the first shelf is exactly 5 px out of max-jump reach, so every run started with an unplanned detour (and the under-shelf ceiling blocks the direct re-mount). Fix: spawn `y=276` = standing on the shelf.

Also added an inert `?probe=1` hook (exposes runner state + two helpers for automated tests only; zero effect in normal play).

**End-to-end verification (headless Chromium, scripted keyboard, no state tampering):** A climbs shelf → shelf → hearth arch; Space toggles to B; B crosses both shelves and the drop into the arch; H swaps the baton (`s1=idle, s2=baton`); care bonus 100 posts; crescent spawns (302 gold px sampled); timer keeps ticking 5+ s after handoff (no freeze); zero page errors. Full run: `/root/.openclaw/workspace-builder/probe-shots/relay-keyboard-handoff.png`.

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
