"""Phonetic bucketing and DP variant alignment."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import combinations

from loader import normalize_text
from rules import (
    KNOWN_FALSE_POSITIVE_PAIRS,
    KNOWN_SHORT_VARIANTS,
    NASAL_PREFIX_RE,
    VALID_SINGLE_SUBS,
    VOWELS,
    is_nasal_prefix_position,
    valid_dr_context,
)


def get_phonetic_skeleton(word: str) -> str:
    """map selected Filipino spelling patterns to a shared canonical skeleton."""
    word = normalize_text(word).replace("-", "")

    # 1. Normalize nasal prefix alternations: pang-/pan-/pam-, mang-/man-/mam-, etc.
    match = NASAL_PREFIX_RE.match(word)
    if match:
        base = match.group("base")
        word = base + "N" + word[match.end():]

    # 2. Normalize glide reductions before vowels: iy -> y, uw -> w.
    word = re.sub(r"iy(?=[aeiou])", "y", word)
    word = re.sub(r"uw(?=[aeiou])", "w", word)

    # 3. Canonicalize vowel shifts (e -> i, o -> u) and d/r shifts (r -> d).
    return word.replace("e", "i").replace("o", "u").replace("r", "d")


def divide_into_buckets(vocab_counts: Counter[str]) -> dict[str, list[str]]:
    """partition vocabs into small phonetic buckets"""
    buckets: dict[str, list[str]] = defaultdict(list)
    for word in vocab_counts:
        if len(word.replace("-", "")) < 3:
            continue
        skeleton = get_phonetic_skeleton(word)
        buckets[skeleton].append(word)
    return {key: words for key, words in buckets.items() if len(words) >= 2}


def align_and_validate_dp(
    word1: str,
    word2: str,
    max_edits: int = 2,
    dedup_diffs: bool = True,
) -> tuple[bool, str, int | None]:
    """
    Weighted DP alignment using only valid Filipino orthographic shifts.
    Returns (accepted, character_difference, edit_cost).
    """
    word1 = normalize_text(word1)
    word2 = normalize_text(word2)

    if word1 == word2:
        return False, "", 0

    pair_key = frozenset((word1, word2))
    if pair_key in KNOWN_FALSE_POSITIVE_PAIRS:
        return False, "", None

    # guard against 3- and 4-letter minimal pairs (e.g. opo/upo, pare/pari, basa/baso)
    # unless explicitly listed in KNOWN_SHORT_VARIANTS (e.g. dito/rito, ito/eto).
    clean_len1 = len(word1.replace("-", ""))
    clean_len2 = len(word2.replace("-", ""))
    if max(clean_len1, clean_len2) <= 4 and pair_key not in KNOWN_SHORT_VARIANTS:
        return False, "", None

    n, m = len(word1), len(word2)
    inf = 10**9
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int, str] | None]] = [
        [None] * (m + 1) for _ in range(n + 1)
    ]
    dp[0][0] = 0

    def relax(ni: int, nj: int, new_cost: int, pi: int, pj: int, label: str) -> None:
        if new_cost < dp[ni][nj]:
            dp[ni][nj] = new_cost
            back[ni][nj] = (pi, pj, label)

    for i in range(n + 1):
        for j in range(m + 1):
            current = dp[i][j]
            if current >= inf or current > max_edits:
                continue

            # 1. Exact character match (cost 0).
            if i < n and j < m and word1[i] == word2[j]:
                relax(i + 1, j + 1, current, i, j, "")

            # 2. Valid 1-to-1 phonological substitution: o/u, e/i, d/r (cost 1).
            if i < n and j < m and frozenset((word1[i], word2[j])) in VALID_SINGLE_SUBS:
                sub_pair = frozenset((word1[i], word2[j]))
                allowed = True
                if sub_pair == frozenset(("d", "r")):
                    allowed = valid_dr_context(word1, i) and valid_dr_context(word2, j)
                if allowed:
                    relax(
                        i + 1, j + 1, current + 1, i, j,
                        f"{word1[i]} vs. {word2[j]}",
                    )

            # 3. Nasal assimilation in prefix position: ng <-> n/m (cost 1).
            if i + 1 < n and j < m and word1[i:i + 2] == "ng" and word2[j] in {"n", "m"}:
                if (
                    is_nasal_prefix_position(word1, i, 2)
                    and is_nasal_prefix_position(word2, j, 1)
                ):
                    relax(i + 2, j + 1, current + 1, i, j, f"ng vs. {word2[j]}")

            if i < n and j + 1 < m and word1[i] in {"n", "m"} and word2[j:j + 2] == "ng":
                if (
                    is_nasal_prefix_position(word1, i, 1)
                    and is_nasal_prefix_position(word2, j, 2)
                ):
                    relax(i + 1, j + 2, current + 1, i, j, f"{word1[i]} vs. ng")

            # 4. Glide reduction before a vowel: iy <-> y, uw <-> w (cost 1).
            if i + 1 < n and j < m:
                pair1 = word1[i:i + 2]
                if pair1 in {"iy", "uw"} and word2[j] == pair1[1]:
                    if i + 2 < n and j + 1 < m and word1[i + 2] in VOWELS and word2[j + 1] in VOWELS:
                        relax(i + 2, j + 1, current + 1, i, j, f"{pair1} vs. {word2[j]}")

            if i < n and j + 1 < m:
                pair2 = word2[j:j + 2]
                if pair2 in {"iy", "uw"} and word1[i] == pair2[1]:
                    if j + 2 < m and i + 1 < n and word2[j + 2] in VOWELS and word1[i + 1] in VOWELS:
                        relax(i + 1, j + 2, current + 1, i, j, f"{word1[i]} vs. {pair2}")

            # 5. Hyphen insertion/deletion (cost 1).
            if i < n and word1[i] == "-":
                relax(i + 1, j, current + 1, i, j, "- vs. none")
            if j < m and word2[j] == "-":
                relax(i, j + 1, current + 1, i, j, "none vs. -")

    total_cost = dp[n][m]
    if total_cost == inf or total_cost == 0 or total_cost > max_edits:
        return False, "", None

    # backtrack to reconstruct character differences in left-to-right order.
    differences: list[str] = []
    i, j = n, m
    while i > 0 or j > 0:
        previous = back[i][j]
        if previous is None:
            return False, "", None
        pi, pj, label = previous
        if label:
            differences.append(label)
        i, j = pi, pj

    differences.reverse()
    if dedup_diffs:
        differences = list(dict.fromkeys(differences))
    return True, "; ".join(differences), total_cost


def find_all_spelling_variants(
    vocab_counts: Counter[str],
    buckets: dict[str, list[str]] | None = None,
    max_edits: int = 2,
    dedup_diffs: bool = True,
) -> list[dict[str, object]]:
    """Verify candidate pairs within each bucket using weighted DP."""
    if max_edits < 1:
        raise ValueError("max_edits must be at least 1")

    if buckets is None:
        buckets = divide_into_buckets(vocab_counts)

    results: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for words in buckets.values():
        words_sorted = sorted(set(words))
        for word1, word2 in combinations(words_sorted, 2):
            if abs(len(word1) - len(word2)) > max_edits:
                continue
            pair = (word1, word2)
            if pair in seen:
                continue
            seen.add(pair)

            accepted, difference, cost = align_and_validate_dp(
                word1, word2, max_edits=max_edits, dedup_diffs=dedup_diffs
            )
            if accepted:
                results.append({
                    "word1": word1,
                    "word2": word2,
                    "word1_count": vocab_counts[word1],
                    "word2_count": vocab_counts[word2],
                    "character_difference": difference,
                    "_edit_cost": cost,
                })

    # sort by highest combined frequency first, then alphabetically.
    results.sort(
        key=lambda row: (
            -(int(row["word1_count"]) + int(row["word2_count"])),
            str(row["word1"]),
            str(row["word2"]),
        )
    )
    for row in results:
        row.pop("_edit_cost", None)
    return results