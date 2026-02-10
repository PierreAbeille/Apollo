# Grid Balancing Lab

Ablation + balancing explorer for the ML models (taste and emotion).
Tests combinations of feature blocks and balancing strategies via cross-validation,
then outputs a reproducible report with a recommended "default config".

## Quick Start

```bash
cd /path/to/Apollo/apps/ml

# Preview experiment plan (no execution)
python tools/gridlab.py --task taste --dry-run
python tools/gridlab.py --task emotion --dry-run

# Full run — taste (default: 5-fold CV, seed 42)
python tools/gridlab.py --task taste --output reports/

# Full run — emotion
python tools/gridlab.py --task emotion --output reports/

# Custom options
python tools/gridlab.py \
  --task taste \
  --kw-sizes 0,100,300 \
  --balancing none,class_weight,undersample \
  --cv 5 \
  --seed 42 \
  --output reports/
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--task` | *required* | `taste` or `emotion` |
| `--kw-sizes` | `0,100,300` | Comma-separated keyword vocab sizes |
| `--balancing` | `none,class_weight,undersample` | Strategies to test |
| `--cv` | `5` | Number of stratified CV folds |
| `--seed` | `42` | Random seed for reproducibility |
| `--output` | `reports/` | Output directory |
| `--max-configs` | `20` | Safety cap (use `--force` to override) |
| `--force` | — | Skip the safety cap |
| `--dry-run` | — | Print plan, don't execute |

## Feature Blocks

### Taste
| Block | Features |
|-------|----------|
| `COS_POS` | `cos_pos_c*`, `max/min/mean_cos_pos` |
| `NEG` | `cos_to_neg_center`, `pos_neg_margin` |
| `META` | `lang_*`, `decade_*`, `release_year_normalized` |
| `GENRE` | `genre_*` |
| `KW` | `kw_*` (sliced by `--kw-sizes`) |

### Emotion
| Block | Features |
|-------|----------|
| `ANCHOR` | `anchor_*` (8 z-scored logits) |
| `GENRE` | `genre_*` |
| `KW` | `kw_*` (sliced by `--kw-sizes`) |

## Output

Each run generates two files in `--output`:

- `gridlab_<task>_<timestamp>.json` — full results with per-fold data
- `gridlab_<task>_<timestamp>.md` — human-readable report with:
  - Ranked comparison table
  - Stability analysis (mean ± std, CV coefficient)
  - Auto-generated insights
  - Final recommendation (blocks + kw_size + balancing + feature count)
