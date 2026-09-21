# OpenType Layout Features Specification: Nokora Font

[![OpenType](https://img.shields.io/badge/OpenType-GSUB%20%2F%20GPOS-blue.svg)](#)
[![Script](https://img.shields.io/badge/Script-Khmer%20(khmr)-green.svg)](#)
[![Shaper](https://img.shields.io/badge/Shaper-HarfBuzz%20%7C%20DirectWrite%20%7C%20CoreText-orange.svg)](#)

Technical specification and layout architecture for the OpenType tables (**GSUB**, **GPOS**, **GDEF**) of the **Nokora** typeface family.

---

## 1. Overview & Design Rationale

**Nokora** is an accessible, high-legibility Unicode Khmer typeface designed primarily for user interfaces (UI/UX), mobile operating environments, and digital displays. Rather than supporting ornate or calligraphic script ligatures, Nokora's OpenType structure focuses on precision and execution performance:

* **Lightweight Shaping Pipeline:** Avoids decorative or arbitrary glyph-to-glyph ligature pairs. The layout code focuses on mandatory Khmer orthographic transformations: sub-consonant (Coeng) synthesis, compound vowel decomposition, and systematic vertical collision avoidance.
* **Screen Clarity at Small Sizes:** Utilizes contextual variants—lowered (`.b`), elevated (`.a`), and right-shifted (`.r`)—alongside targeted GPOS rules to maintain clear counters and prevent stroke overlap in dense text environments.
* **Cross-Engine Determinism:** Tested and calibrated to behave identically across modern shaper engines, including **HarfBuzz**, **DirectWrite / Uniscribe**, and **CoreText**.

---

## 2. Glyph Naming Conventions & Classes

The table below describes the glyph classification scheme used throughout the feature code:

| Category | Identifier / Pattern | Description & Function |
| :--- | :--- | :--- |
| **Base Consonants** | `uni1780` – `uni17A2` | Base consonant stems and independent vowels. |
| **Below-Base Coeng** | `sub80` – `subA2` | Primary below-base sub-consonants formed via `uni17D2 + Consonant`. |
| **Post-Base Coeng** | `sub83`, `sub88`, `sub8D`, `sub94`, `sub99`, `sub9F` | Sub-consonants with right-ascending stems (Kho, Chho, Ttho, Ba, Yo, Sa). |
| **Pre-Base Coeng** | `sub9A` | Coeng Ro, reordered to the left side of the syllable cluster by the engine. |
| **Lowered Variants (`.b`)** | `uni17BB.b`, `sub9A.b`, `sub83.b`... | Deep-drop alternates positioned to clear intermediate descending marks. |
| **Elevated Variants (`.a`)** | `uni17B7.a` – `uni17D0.a`, `uni1794.a` | Raised marks for mark-over-mark stacking, or connecting forms (e.g., Ba). |
| **Shifted Variants (`.r`)** | `uni17B7.r` – `uni17CD.r` | Horizontally shifted marks calibrated for narrow or curved base consonants. |
| **Right Stems** | `uni17BF.right`, `uni17C0.right`, `uni17C5.right` | Standalone post-base vertical elements of decomposed vowels. |

---

## 3. GSUB Pipeline Architecture

Lookup execution follows the standard OpenType shaping order for the Khmer script:

```mermaid
graph TD
    A[Raw Unicode Stream] --> B[pref: Form Coeng Ro]
    B --> C[blwf: Form Below Coeng]
    C --> D[pstf: Form Post-base Coeng]
    D --> E[pres: Extend Coeng Ro sweep sub9A.b]
    E --> F[blws: Nyo cut uni1789.a, Ba open form uni1794.a, Lower vowels .b]
    F --> G[abvf: Decompose split vowels OE]
    G --> H[abvs: Convert shifters ៉/៊ to ុ, Elevate .a, Shift .r]
    H --> I[psts: Decompose right pieces .right, Lower tier-2 coeng .b]
    I --> J[Shaped Glyph Stream]