from __future__ import annotations

import argparse
import csv
from typing import Iterable

from detector import align_and_validate_dp, divide_into_buckets, find_all_spelling_variants
from loader import build_vocab


def export_to_csv(results: Iterable[dict[str, object]], output_filepath: str) -> None:
    """Write the required five-column UTF-8 CSV."""
    fieldnames = [
        "word1", "word2", "word1_count", "word2_count", "character_difference"
    ]
    with open(output_filepath, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def run_self_tests() -> None:
    """Verify prompt examples and team research cases."""
    test_cases = [
        ("politiko", "pulitiko", True, "o vs. u"),
        ("lalaki", "lalake", True, "i vs. e"),
        ("totoo", "tutuo", True, "o vs. u"),
        ("dito", "rito", True, "d vs. r"),
        ("marami", "madami", True, "r vs. d"),
        ("pangbuhos", "pambuhos", True, "ng vs. m"),
        ("panlinis", "panglinis", True, "n vs. ng"),
        ("biyaya", "byaya", True, "iy vs. y"),
        ("pag-ibig", "pagibig", True, "- vs. none"),
        ("opo", "upo", False, ""),
        ("polittico", "pulitiko", False, ""),
        ("pare", "pari", False, ""),
        ("madikit", "marikit", False, ""),
    ]

    print("=== RUNNING UNIT TESTS ===")
    all_passed = True
    for w1, w2, expected_valid, expected_diff in test_cases:
        accepted, diff, _ = align_and_validate_dp(w1, w2)
        passed = (accepted == expected_valid) and (diff == expected_diff)
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {w1} vs. {w2} -> valid={accepted}, diff={diff!r}")

    if not all_passed:
        raise SystemExit(1)
    print("All tests passed!\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filipino spelling-variant detector")
    parser.add_argument("input", nargs="?", help="Dataset path (.txt, .csv, .tsv, .jsonl, .json, .db, .sql)")
    parser.add_argument("--out", default="spelling_variants.csv", help="Output CSV path")
    parser.add_argument("--col", default=None, help="Text column name for CSV/TSV/JSONL/JSON/SQLite")
    parser.add_argument("--table", default=None, help="Table name for SQLite databases")
    parser.add_argument("--min-count", type=int, default=1, help="Minimum word frequency (default: 1)")
    parser.add_argument("--max-edits", type=int, default=2, help="Maximum allowed orthographic changes")
    parser.add_argument(
        "--no-dedup-diffs",
        action="store_true",
        help="Repeat identical shifts in character_difference (e.g. 'o vs. u; o vs. u')",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the 20 shortest accepted word pairs to spot-check for false positives",
    )
    parser.add_argument("--test", action="store_true", help="Run built-in unit tests and exit")
    args = parser.parse_args()

    if args.test:
        run_self_tests()
        return

    if not args.input:
        parser.error("the following arguments are required: input (or use --test)")

    print(f"[1/3] Reading and counting words from {args.input}...")
    vocab = build_vocab(
        args.input,
        min_count=args.min_count,
        text_column=args.col,
        table_name=args.table,
    )
    print(f"      Unique words retained: {len(vocab):,}")

    print("[2/3] Generating and verifying candidate pairs...")
    buckets = divide_into_buckets(vocab)
    comparisons = sum(len(words) * (len(words) - 1) // 2 for words in buckets.values())
    print(f"      Candidate buckets: {len(buckets):,}")
    print(f"      Maximum pair comparisons before filtering: {comparisons:,}")

    results = find_all_spelling_variants(
        vocab,
        buckets=buckets,
        max_edits=args.max_edits,
        dedup_diffs=not args.no_dedup_diffs,
    )
    print(f"      Accepted pairs: {len(results):,}")

    if args.preview and results:
        print("\n--- PREVIEW: 20 SHORTEST ACCEPTED PAIRS (CHECK FOR FALSE POSITIVES) ---")
        shortest = sorted(results, key=lambda r: (len(str(r["word1"])), str(r["word1"])))[:20]
        for row in shortest:
            print(
                f"  {row['word1']} ({row['word1_count']}) vs. "
                f"{row['word2']} ({row['word2_count']}) -> [{row['character_difference']}]"
            )
        print("-----------------------------------------------------------------------\n")

    print(f"[3/3] Writing {args.out}...")
    export_to_csv(results, args.out)
    print("Done.")


if __name__ == "__main__":
    main()