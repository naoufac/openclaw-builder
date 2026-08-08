# Telegram ID Market — Product Plan

**Concept:** A marketplace for rare, collectible, and brandable Telegram usernames, channel links, and group handles. Escrowed on TON. 1% trading fee. Built with comedy as a filter.

**Founders:** openclaw-builder (tech) + Nao (business/operations). Revenue/profit share TBD. Not a legal 51/49 ownership split because the builder is an AI agent.

**Status:** Landing page built. Smart contract escrow not yet written. Not live. No token minted.

---

## 1. Problem

Telegram has 1+ billion users. Short, memorable, and culturally funny usernames are already scarce. Fragment (Telegram's own marketplace) only auctions usernames to be assigned to channels, groups, and accounts. There is no easy escrow marketplace for peer-to-peer sales of already-claimed collectible usernames, especially with comedic or brand value.

## 2. Solution

A dedicated marketplace where sellers list Telegram IDs, buyers browse, and a smart contract escrow handles payment release only after transfer is confirmed.

## 3. Scope — what we sell

- **Usernames:** @short, @rare, @funny handles.
- **Channel links:** t.me/brandname handles.
- **Group links:** t.me/groupname handles.

We do **not** sell full Telegram accounts (with message history, contacts, etc.) because that is against Telegram's Terms of Service and is legally high-risk.

## 4. Marketplace mechanics

| Item | Detail |
|------|--------|
| Listing | Seller sets price in TON or USDT. |
| Discovery | Search, filter by category, length, word type, "meme score." |
| Escrow | Smart contract locks buyer funds. |
| Transfer | Seller initiates Telegram's official username transfer to the buyer's account. |
| Release | Buyer confirms transfer on-chain; funds release to seller. |
| Dispute | If transfer fails, dispute resolution with evidence (screenshots, Telegram API proof). |
| Fee | 1% total: 0.5% buyer, 0.5% seller. |

## 5. Token utility ($IDMK — placeholder)

**Important:** The token is a utility/discount token. It is not a security. It does not promise profit derived from the platform's efforts.

- **Fee discount:** Pay fees in $IDMK → 50% discount.
- **Verified seller stake:** Lock $IDMK to receive a verified badge and higher listing rank.
- **Dispute voting:** High-stake holders can vote on disputed escrows (quadratic voting, with skin in the game).
- **Burn:** 1% of trading fees are used to buy and burn $IDMK, reducing supply over time. This is a mechanical feature, not a guaranteed value increase.

Token is not minted until the marketplace has real users and legal clarity.

## 6. Tech stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Blockchain | TON | Telegram-native, fast, low fees, Fragment already uses it. |
| Wallet | TON Connect | Native Telegram wallet support. |
| Smart contract | FunC / Tact | Escrow contract with dispute resolution. |
| Backend | Node.js / Python | Index listings, verify transfers, handle disputes. |
| Frontend | Telegram Mini App + web | React or plain HTML/JS. |
| Identity | Telegram login widget | Avoid separate auth. |

## 7. MVP steps for tonight

1. ✅ Landing page (done).
2. ⬜ Define escrow contract requirements.
3. ⬜ Deploy TON testnet escrow contract.
4. ⬜ Basic Mini App skeleton with TON Connect.
5. ⬜ Listing API (off-chain first, on-chain fees later).
6. ⬜ Waitlist / follow mechanism.

## 8. Legal / risk notes

- **Telegram ToS:** Selling accounts is prohibited. We sell only transferable username/channel handles.
- **KYC/AML:** High-value trades may require identity verification. This depends on jurisdiction.
- **Securities:** $IDMK must be utility-only. No profit promises, no dividends, no fractional ownership of the platform.
- **Jurisdiction:** Nao is based in Morocco/Thailand. We need to confirm where the legal entity is formed and where users are.
- **Dispute liability:** The platform should not take custody of funds. The smart contract should hold funds and release based on oracle/confirmation, not platform discretion.

## 9. Revenue model

- 1% per trade (0.5% buyer + 0.5% seller).
- Optional featured listings paid in $IDMK or TON.
- Optional verified seller badge subscription.

## 10. Open questions

- What domain will Nao provide?
- Should we build on TON testnet first, then mainnet?
- Do we need an off-chain backend for indexing, or purely on-chain?
- What jurisdiction will host the legal entity?
- How is the dispute oracle implemented (Telegram API, trusted verifier, or token-holder vote)?

## 11. Decision needed from Nao

1. Confirm scope: usernames + channel/group handles only, no account sales.
2. Confirm token model: utility-only, no profit promise.
3. Share domain name when home.
4. Confirm next build priority: testnet escrow contract vs. Mini App UI.

---

*Plan written by openclaw-builder, 2026-08-08.*
