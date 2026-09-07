#!/usr/bin/env python3
"""Unit tests for filter helpers (no browser required)."""

from jht_po_styles import (
    STYLE_RE,
    all_suffixes,
    apply_filters,
    format_output,
    get_primary_suffix,
    normalize_style,
    parse_suffix_list,
    unicode_strike,
)


def test_suffix_helpers():
    assert get_primary_suffix("C310-1-2234") == "2234"
    assert get_primary_suffix("C310-1-2273+2274") == "2273"
    assert get_primary_suffix("C310-1-5506/5507/5509") == "5506"
    assert get_primary_suffix("C310-2402") == "2402"
    assert get_primary_suffix("C310-T001") == "T001"
    assert all_suffixes("C310-1-5506/5507") == ["5506", "5507"]
    assert all_suffixes("C310-1-2273+2274") == ["2273", "2274"]
    assert all_suffixes("C310-2402") == ["2402"]


def test_normalize_leading_colon():
    assert normalize_style(":C310-1-6123") == "C310-1-6123"
    assert normalize_style("：C310-1-6123") == "C310-1-6123"
    assert normalize_style("  :C310-1-2231  ") == "C310-1-2231"
    assert normalize_style("C310-1-2231") == "C310-1-2231"
    assert normalize_style("款号：:C310-1-6123") == "C310-1-6123"


def test_style_regex_variants():
    assert STYLE_RE.match("C310-1-2231")
    assert STYLE_RE.match("C301-1-6464")  # other series; was missed when regex was C310-only
    assert STYLE_RE.match("C310-1-2267+2268")
    assert STYLE_RE.match("C310-1-2963/6033")
    assert STYLE_RE.match("C310-1-6154/T001")
    assert STYLE_RE.match("C310-2402")
    assert STYLE_RE.match("C310-T001")
    assert not STYLE_RE.match("C310")
    assert not STYLE_RE.match("C30-1-1234")  # need 3-digit series
    assert not STYLE_RE.match(":C310-1-6123")  # raw; use normalize_style


def test_normalize_other_series():
    assert normalize_style("C301-1-6464") == "C301-1-6464"
    assert normalize_style(":C301-1-6464") == "C301-1-6464"


def test_parse_suffix_list():
    assert parse_suffix_list("2234.2275.5507.") == {"2234", "2275", "5507"}
    assert parse_suffix_list("2780,2763") == {"2780", "2763"}


def test_cutoff_and_skip():
    styles = [
        ":C310-1-6123",  # leading colon from page
        "C310-1-2231",
        "C310-1-2780",
        "C310-1-5522/T001",
        "C310-1-6027",
        "C310-1-6032",
    ]
    r = apply_filters(
        styles, until="6027", inclusive=False, skip={"2780"}, strike=set()
    )
    assert r.styles == ["C310-1-6123", "C310-1-2231", "C310-1-5522/T001"]
    assert r.skipped == ["C310-1-2780"]
    r2 = apply_filters(
        styles, until="6027", inclusive=True, skip=set(), strike=set()
    )
    assert r2.styles[-1] == "C310-1-6027"


def test_skip_and_strike_after_full_extract():
    """Skip/strike run only after cutoff; both match any combo segment."""
    styles = [
        "C310-1-2234",
        "C310-1-5506/5507",
        "C310-1-6012",
        "C310-1-6027",
    ]
    r = apply_filters(
        styles,
        until="6027",
        inclusive=False,
        skip={"5507"},  # secondary segment of combo
        strike={"2234"},
    )
    assert r.styles == ["C310-1-2234", "C310-1-6012"]
    assert r.skipped == ["C310-1-5506/5507"]
    assert r.struck == ["C310-1-2234"]
    assert r.unmatched_skip == []
    assert r.unmatched_strike == []


def test_strike_matches_combo_segments():
    styles = ["C310-1-2234", "C310-1-5506/5507", "C310-1-6012"]
    r = apply_filters(
        styles, until=None, inclusive=False, skip=set(), strike={"5507", "2234"}
    )
    assert set(r.struck) == {"C310-1-2234", "C310-1-5506/5507"}
    assert r.unmatched_strike == []
    out = format_output(
        r.styles, strike={"5507", "2234"}, check=set(), md=False, unicode_strike_mode=False
    )
    assert "~~C310-1-2234~~" in out
    assert "~~C310-1-5506/5507~~" in out
    assert "C310-1-6012" in out.splitlines()


def test_unicode_strike():
    s = unicode_strike("AB")
    assert "\u0336" in s
    assert s[0] == "A"


if __name__ == "__main__":
    test_suffix_helpers()
    test_normalize_leading_colon()
    test_style_regex_variants()
    test_parse_suffix_list()
    test_cutoff_and_skip()
    test_skip_and_strike_after_full_extract()
    test_strike_matches_combo_segments()
    test_unicode_strike()
    print("ok")
