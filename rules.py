"""Filipino orthographic rules, phonological contexts, and lexical guardrails."""

from __future__ import annotations

import re

# unicode letters, optionally joined by internal hyphens (e.g. araw-araw)
LETTER = r"[^\W\d_]"
WORD_RE = re.compile(rf"{LETTER}+(?:-{LETTER}+)*", re.UNICODE)
VOWELS = "aeiou"
CONSONANTS = "bcdfghjklmnpqrstvwxyz"

# valid 1 to 1 single-character substitutions
VALID_SINGLE_SUBS = {
    frozenset(("o", "u")),
    frozenset(("e", "i")),
    frozenset(("d", "r")),
}

# explicitly known false positive pairs
KNOWN_FALSE_POSITIVE_PAIRS: set[frozenset[str]] = {
    frozenset(("opo", "upo")),
    frozenset(("pare", "pari")),
    frozenset(("madikit", "marikit")),
    frozenset(("kulang", "kulong")),
    frozenset(("sukat", "sukot")),
    frozenset(("lamang", "lamong")),
    frozenset(("buhay", "buhoy")),
    frozenset(("puno", "puna")),
    frozenset(("basa", "baso")),
    frozenset(("basa", "base")),
    frozenset(("mesa", "misa")),
    frozenset(("tila", "tula")),
}

# valid 3- and 4-letter spelling variants
KNOWN_SHORT_VARIANTS: set[frozenset[str]] = {
    frozenset(("ito", "eto")),
    frozenset(("iyan", "eyan")),
    frozenset(("iyon", "eyon")),
    frozenset(("dito", "rito")),
    frozenset(("diyan", "riyan")),
    frozenset(("doon", "roon")),
    frozenset(("dini", "rini")),
    frozenset(("daw", "raw")),
    frozenset(("din", "rin")),
    frozenset(("ano", "anu")),
    frozenset(("sino", "sinu")),
}

# prefix material before the nasal segment in pang-/pan-/pam- and mang-/man-/mam- forms.
NASAL_PREFIX_BASES = (
    "makapa", "nakapa", "mapa", "napa", "kapa", "ipa", "pa", "ma", "sa", "hi", "si"
)
NASAL_PREFIX_RE = re.compile(
    r"^(?P<base>makapa|nakapa|mapa|napa|kapa|ipa|pa|ma|sa|hi|si)"
    r"(?:ng|n|m)(?=[bcdfghjklmnpqrstvwxyz])"
)


def valid_dr_context(word: str, index: int) -> bool:
    """allow d <-> r alternation only word-initially or intervocalically"""
    if index == 0:
        return True
    return (
        0 < index < len(word) - 1
        and word[index - 1] in VOWELS
        and word[index + 1] in VOWELS
    )


def is_nasal_prefix_position(word: str, index: int, segment_length: int) -> bool:
    """permit ng <-> n/m only immediately after a recognized prefix base before a consonant."""
    prefix = word[:index]
    suffix_start = index + segment_length
    return (
        prefix in NASAL_PREFIX_BASES
        and suffix_start < len(word)
        and word[suffix_start] in CONSONANTS
    )