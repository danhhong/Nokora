#!/usr/bin/env python3
"""
Interpolate 9 static weight instances (Thin..Black) from 3 compatible
TrueType masters using fontTools.

Requires: pip install fonttools
"""

import os
from copy import deepcopy
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.misc.fixedTools import otRound

# ---------------------------------------------------------------------------
# Master font paths & configuration
# ---------------------------------------------------------------------------

THIN_PATH = "Nokora-Thin.ttf"
REGULAR_PATH = "Nokora-Regular.ttf"
BLACK_PATH = "Nokora-Black.ttf"

OUTPUT_DIR = "outputs"
FAMILY_NAME = "Nokora"

# Format: (weight_name, usWeightClass, is_bold_link)
# Only weight 700 (Bold) links to Regular (400) via the B button.
WEIGHTS = [
    ("Thin",       100, False),
    ("ExtraLight", 200, False),
    ("Light",      300, False),
    ("Regular",    400, False),
    ("Medium",     500, False),
    ("SemiBold",   600, False),
    ("Bold",       700, True),
    ("ExtraBold",  800, False),
    ("Black",      900, False),
]

# ---------------------------------------------------------------------------
# Interpolation math & glyph processing
# ---------------------------------------------------------------------------

def lerp(a, b, t):
    """Linearly interpolate between numbers a and b at factor t, rounded to int."""
    return otRound(a + (b - a) * t)


def interpolate_glyph(glyf_lo, glyf_hi, name, t):
    """
    Linearly interpolate glyph point coordinates between two masters.
    Handles empty glyphs, simple contours, and composite component offsets.
    """
    g_lo = glyf_lo[name]
    g_hi = glyf_hi[name]
    new_glyph = deepcopy(g_lo)

    # Composite glyph: interpolate placement offsets for all components
    if g_lo.numberOfContours < 0:
        for comp_new, comp_hi in zip(new_glyph.components, g_hi.components):
            if hasattr(comp_new, "x") and hasattr(comp_hi, "x"):
                comp_new.x = lerp(comp_new.x, comp_hi.x, t)
                comp_new.y = lerp(comp_new.y, comp_hi.y, t)
        return new_glyph

    # Empty glyph (e.g. space, nonmarkingreturn)
    if g_lo.numberOfContours == 0:
        return new_glyph

    coords_lo, _, _ = g_lo.getCoordinates(glyf_lo)
    coords_hi, _, _ = g_hi.getCoordinates(glyf_hi)

    if len(coords_lo) != len(coords_hi):
        raise ValueError(
            f"Point count mismatch for glyph '{name}': {len(coords_lo)} vs {len(coords_hi)}"
        )

    new_points = [
        (lerp(x0, x1, t), lerp(y0, y1, t))
        for (x0, y0), (x1, y1) in zip(coords_lo, coords_hi)
    ]
    new_glyph.coordinates = GlyphCoordinates(new_points)
    return new_glyph


def interpolate_hmtx(hmtx_lo, hmtx_hi, name, t):
    """Interpolate advance width and left side bearing for a glyph."""
    aw_lo, lsb_lo = hmtx_lo[name]
    aw_hi, lsb_hi = hmtx_hi[name]
    return lerp(aw_lo, aw_hi, t), lerp(lsb_lo, lsb_hi, t)


# ---------------------------------------------------------------------------
# Weight instance builder
# ---------------------------------------------------------------------------

def build_weight(font_lo, font_hi, t, weight_name, weight_class, is_bold, base_metrics_font):
    """
    Build a single static weight instance TTFont by interpolating between two masters,
    locking vertical metrics, and setting up RIBBI style-linking tables.
    """
    out = deepcopy(font_lo)

    glyf_lo = font_lo["glyf"]
    glyf_hi = font_hi["glyf"]
    glyf_out = out["glyf"]
    hmtx_lo = font_lo["hmtx"]
    hmtx_hi = font_hi["hmtx"]
    hmtx_out = out["hmtx"]

    # 1. Interpolate outlines and horizontal glyph advance metrics
    for name in out.getGlyphOrder():
        glyf_out[name] = interpolate_glyph(glyf_lo, glyf_hi, name, t)
        glyf_out[name].recalcBounds(glyf_out)
        hmtx_out[name] = interpolate_hmtx(hmtx_lo, hmtx_hi, name, t)

    # 2. Update horizontal header metrics
    hhea_lo, hhea_hi = font_lo["hhea"], font_hi["hhea"]
    out["hhea"].advanceWidthMax = lerp(hhea_lo.advanceWidthMax, hhea_hi.advanceWidthMax, t)

    os2_lo, os2_hi = font_lo["OS/2"], font_hi["OS/2"]
    out["OS/2"].usWeightClass = weight_class
    out["OS/2"].xAvgCharWidth = lerp(os2_lo.xAvgCharWidth, os2_hi.xAvgCharWidth, t)

    # 3. Lock Vertical Metrics across all weights to the Regular master values
    #    (Prevents line jumps/reflow when toggling bold or changing weights)
    reg_os2 = base_metrics_font["OS/2"]
    reg_hhea = base_metrics_font["hhea"]
    out["OS/2"].sTypoAscender  = reg_os2.sTypoAscender
    out["OS/2"].sTypoDescender = reg_os2.sTypoDescender
    out["OS/2"].sTypoLineGap   = reg_os2.sTypoLineGap
    out["OS/2"].usWinAscent    = reg_os2.usWinAscent
    out["OS/2"].usWinDescent   = reg_os2.usWinDescent
    out["hhea"].ascent         = reg_hhea.ascent
    out["hhea"].descent        = reg_hhea.descent
    out["hhea"].lineGap        = reg_hhea.lineGap

    # 4. Configure Style Bits (fsSelection and macStyle)
    if is_bold:
        # Bold instance: enable Bold bits in OS/2 and head
        out["OS/2"].fsSelection |= 0x20     # Bit 5: BOLD
        out["OS/2"].fsSelection &= ~0x40    # Clear Bit 6: REGULAR
        out["head"].macStyle |= 0x1         # Bit 0: Bold
    elif weight_name == "Regular":
        # Regular instance: enable Regular bit
        out["OS/2"].fsSelection |= 0x40     # Bit 6: REGULAR
        out["OS/2"].fsSelection &= ~0x20    # Clear Bit 5: BOLD
        out["head"].macStyle &= ~0x1
    else:
        # Non-standard weights act as their own default style in basic menus
        out["OS/2"].fsSelection &= ~0x20
        out["OS/2"].fsSelection |= 0x40
        out["head"].macStyle &= ~0x1

    # 5. OpenType 'name' Table Configuration (RIBBI + Typographic Naming)
    full_name = f"{FAMILY_NAME} {weight_name}"
    ps_name = f"{FAMILY_NAME}-{weight_name}".replace(" ", "")

    # Preferred Family/Subfamily (nameID 16 / 17): Groups all 9 weights into one family
    pref_family = FAMILY_NAME
    pref_subfamily = weight_name

    # Legacy Family/Subfamily (nameID 1 / 2): Style-linking for MS Office, LibreOffice, etc.
    if is_bold:
        # Bold links directly to "Nokora" as its Bold counterpart
        legacy_family = FAMILY_NAME
        legacy_subfamily = "Bold"
    elif weight_name == "Regular":
        # Regular is the base instance of "Nokora"
        legacy_family = FAMILY_NAME
        legacy_subfamily = "Regular"
    else:
        # Other weights exist as discrete families to prevent 4-style grouping collisions
        legacy_family = f"{FAMILY_NAME} {weight_name}"
        legacy_subfamily = "Regular"

    name_table = out["name"]
    platforms = [(3, 1, 0x409), (1, 0, 0)]  # Windows Unicode BMP, Mac Roman

    for plat_id, enc_id, lang_id in platforms:
        # Remove legacy records to avoid stale master metadata
        for id_to_clean in (1, 2, 4, 6, 16, 17):
            name_table.removeNames(nameID=id_to_clean, platformID=plat_id, platEncID=enc_id, langID=lang_id)

        # Standard RIBBI & Identification records
        name_table.setName(legacy_family, 1, plat_id, enc_id, lang_id)
        name_table.setName(legacy_subfamily, 2, plat_id, enc_id, lang_id)
        name_table.setName(full_name, 4, plat_id, enc_id, lang_id)
        name_table.setName(ps_name, 6, plat_id, enc_id, lang_id)

        # Write Typographic names (nameID 16 & 17) only when they differ from legacy IDs 1 & 2
        if (legacy_family != pref_family) or (legacy_subfamily != pref_subfamily):
            name_table.setName(pref_family, 16, plat_id, enc_id, lang_id)
            name_table.setName(pref_subfamily, 17, plat_id, enc_id, lang_id)

    return out


# ---------------------------------------------------------------------------
# Main orchestration routine
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading masters: {THIN_PATH}, {REGULAR_PATH}, {BLACK_PATH}...")
    thin = TTFont(THIN_PATH)
    regular = TTFont(REGULAR_PATH)
    black = TTFont(BLACK_PATH)

    for weight_name, weight_class, is_bold in WEIGHTS:
        # Choose interpolation segment
        if weight_class <= 400:
            font_lo, font_hi = thin, regular
            span_lo, span_hi = 100, 400
        else:
            font_lo, font_hi = regular, black
            span_lo, span_hi = 400, 900

        # Exact master instances (avoid interpolation overhead)
        if weight_class == 100:
            out = build_weight(thin, thin, 0.0, weight_name, weight_class, is_bold, regular)
        elif weight_class == 400:
            out = build_weight(regular, regular, 0.0, weight_name, weight_class, is_bold, regular)
        elif weight_class == 900:
            out = build_weight(black, black, 0.0, weight_name, weight_class, is_bold, regular)
        else:
            # Interpolate in-between instances
            t = (weight_class - span_lo) / (span_hi - span_lo)
            out = build_weight(font_lo, font_hi, t, weight_name, weight_class, is_bold, regular)

        out_path = os.path.join(OUTPUT_DIR, f"{FAMILY_NAME}-{weight_name}.ttf")
        out.save(out_path)
        print(f"Wrote {out_path:<30} (usWeightClass={weight_class}, BoldLink={is_bold})")

    print("\nAll 9 weights generated successfully with RIBBI style-linking.")


if __name__ == "__main__":
    main()