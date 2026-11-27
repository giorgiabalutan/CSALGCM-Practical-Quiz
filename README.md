# Filipino Spelling-Variant Detector
A Python program that detects possible Filipino spelling variations from text files. It uses Filipino spelling rules, phonetic bucketing, and a modified Dynamic Programming algorithm to identify words with different spellings but potentially similar meanings.

---
## Project Structure
```text
.
├── main.py        # Main program and CSV export
├── loader.py      # Text preprocessing and word counting
├── detector.py    # Phonetic bucketing and DP comparison
├── rules.py       # Filipino spelling rules and restrictions
└── README.md      # Project documentation
```
---
## Requirements
* **Python 3.9+**
* **`pyspellchecker`** (used to filter out English words during tokenization)

Install the dependency via `pip`:
```bash
pip install pyspellchecker
```
---
## Usage

### 1. Quick Start (Default Run)
Run the detector on a `.txt` dataset to generate `spelling_variants.csv`:
```bash
python main.py Raw.txt
```

### 2. Run Built-in Unit Tests
Verify that the orthographic rules and alignment logic pass all test cases:
```bash
python main.py --test
```

### 3. Optional CLI Arguments
Customize thresholds, output paths, or console previews without modifying the source code:
| Flag | Description | Default |
| :--- | :--- | :--- |
| `--out <path>` | Output CSV file path | `spelling_variants.csv` |
| `--min-count <N>` | Minimum frequency required to retain a word | `1` |
| `--max-edits <N>` | Maximum allowed orthographic shifts per pair | `2` |
| `--preview` | Print the 20 shortest accepted pairs in the terminal | Off |
| `--no-dedup-diffs` | Repeat identical shifts in `character_difference` | Off |

**Example:**
```bash
python main.py Raw.txt --min-count 3 --out filtered_variants.csv --preview
```

---
