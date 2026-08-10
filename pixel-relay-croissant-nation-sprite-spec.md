# Croissant Nation — Sprite Spec

*Visual vocabulary for Hardy's pixel-art pass on `pixel-relay-croissant-nation.html`.*

## World palette

- Background: warm parchment (`#1a1208` shadow to `#f4e4bc` paper)
- Platforms: raw dough bands with golden-bake top edge
- Hazards: burnt-crust spikes, dark charred tips
- Hearth arch: stone oven mouth with ember glow
- Crown goal: pastry-king silhouette, warm light rays

## Runners

### Baker A (baton carrier)
- Small white jacket, flour-dusted apron
- Carries a **baguette-wand baton** — long, golden, slight bend
- Run frames: stride with baton bouncing opposite leg
- Jump frame: baton raised, flour poof at feet
- Idle: rolling baton on one palm

### Baker B (receiver / hearth rekindler)
- Same uniform, no baton until handoff completes
- Run frames: arms pumping, ready to receive
- After rekindle: sleeve cuffs glow warm orange briefly
- Victory pose: both hands raised, tiny crown appears above head

## Objects

- **Butter pearl** (orb): small glossy sphere, pale yellow, soft inner sheen
- **Golden crescent** bonus: warm amber crescent, flaky edge shimmer
- **Crumb trail**: tiny drifting particles, orange-to-gold gradient, fades after ~5s
- **Hearth rekindle flash**: arch fills with warm amber light, particles bloom outward

## Effects

- Perfect run: parchment-colored confetti + faint steam / flour dust
- Hazard hit: burnt crumbs spray
- Handoff zone: warm oven-light rectangle, ember-pulse border

## Hook replacements

Replace these functions in `pixel-relay-croissant-nation.html` without touching physics:

- `drawRunner(x, y, w, h, color, hasBaton)` — use color to distinguish A/B
- `drawPlatform({x, y, w, h})`
- `drawHazard({x, y, w, h})`
- `drawOrb({x, y, r})` — butter pearl
- `drawCrescent({x, y, r})` — golden crescent bonus
- `drawGoal({x, y, w, h})` — crown goal
- `drawHandoffZone({x, y, w, h})` — hearth arch
- `drawCrumbTrail(ctx)` — golden crumb particles

## Reference

- Sprite Hook Reference: https://naoufac.github.io/openclaw-builder/pixel-relay-sprite-hooks.html
- Live level: https://naoufac.github.io/openclaw-builder/pixel-relay-croissant-nation.html
