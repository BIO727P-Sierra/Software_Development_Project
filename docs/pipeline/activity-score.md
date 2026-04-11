# Step 6: Activity Score Calculation

## What this step does

Activity score calculation executes automatically at the end of the analysis step, after mutation calling has completed. No additional user action is required. Calculated scores are stored in the database, displayed in the **Top 10 Performers** table, and used in downstream [visualisations](visualisations.md).

The activity score compares a variant's DNA yield to its protein yield, normalised against a wild-type (WT) control baseline, on a log₂ scale.

---

## For scientists

### Interpreting the score

Activity scores greater than zero indicate that a variant has **greater activity** than the baseline (WT control). Values below zero indicate **decreased activity** relative to the baseline.

Because the score is on a log₂ scale, changes should be interpreted as fold differences:

| Score | Fold difference vs baseline |
|---|---|
| `+1` | ~2-fold higher activity |
| `+2` | ~4-fold higher activity |
| `0` | equal to baseline |
| `-1` | ~half of baseline |

### Top 10 performing variants table

The Top 10 Performing Variants table ranks the best-performing variants by unified activity score so users can quickly identify top candidates. It is accessible from the experiment results page via the **Top 10 Performers** button above the ORF Analysis Results table.

| Visualisation | Route |
|---|---|
| Top 10 Performing Variants | `/analysis/results/experiment/<experiment_id>/top-performers` |

Rows are sorted by activity score descending (highest first), excluding control rows and showing only variants with a valid score. For each of the 10 variants, the table displays DNA and protein yields, activity scores, and mutation totals. Column heading tooltips describe the information contained in each column in more detail.

### Limitations

The activity score relies heavily on WT control measurements for baseline normalisation. To ensure scores can still be computed when ideal controls are unavailable, a three-level fallback is applied:

1. Strict WT controls within the same generation
2. Any controls within the same generation
3. Any controls in the experiment

While this fallback system ensures robustness, it introduces potential limitations: controls from different generations or across the experiment may be subject to batch effects, sequencing variation, library preparation differences, or changes in experimental conditions. These factors may affect baseline values and, therefore, influence the resulting activity scores.

Additionally, the activity score calculation relies on averaged DNA and protein yield measurements, so the scores may not fully capture variability between replicate measurements.

---

## For developers

### Route

Activity scoring is triggered internally within the Step 1 analysis route:

| Method | URL | Handler |
|---|---|---|
| `POST` | `/analysis/step1/run_experiment/<experiment_id>` | `analysis.run_step1` |

### Set-up and inputs

`app/analysis_score.py` imports Python's `math` library to use `math.log2()` for the final scoring scale, returning a float value representing the base-2 logarithm of a number. The `compute_activity_score()` function is the main scoring entry point. It takes four values from the database and two guard values as parameters.

**Database inputs**

| Input | Description |
|---|---|
| `dna_yield` | Average DNA yield for each variant, taken from the `measurements` table |
| `protein_yield` | Average protein yield for each variant, taken from the `measurements` table |
| `dna_baseline` | Average DNA baseline taken from WT control measurements |
| `protein_baseline` | Average protein baseline taken from WT control measurements |

**Guard values**

| Input | Description |
|---|---|
| `epsilon` | Declared as `1e-6` — prevents divide-by-zero errors and ensures numerical stability when normalising the DNA and protein yields by baselines |
| `min_protein` | Protein threshold preventing scoring of variants with negligible protein yields |

### Validation

Validation is split into two stages:

1. **Missing values check** — if `dna_yield` or `protein_yield` is missing, the function raises `ValueError`.
2. **Low protein filter** — if `protein_yield` is below the minimum protein threshold of `0.01`, the score is skipped and the function returns `None`.

### Calculation logic

The activity score is calculated in two steps.

**Step 1: Baseline normalisation** — DNA and protein yield are normalised by their respective baseline values taken from WT control measurements for the same generation:

```python
dna_fold = float(dna_yield) / max(float(dna_baseline), epsilon)
protein_fold = float(protein_yield) / max(float(protein_baseline), epsilon)
```

**Step 2: DNA yield normalisation by protein yield, with log₂ scaling**:

```python
score = math.log2(dna_fold / max(protein_fold, epsilon))
```

The final activity score is stored in the variable `score` and returned.

### Helper functions

| Helper | Purpose |
|---|---|
| `_load_experiment_generations(cur, experiment_id)` | Finds all unique generation numbers for an experiment, sorted ascending, and returns as a list |
| `_load_wt_baseline_for_generation(cur, experiment_id, generation)` | Retrieves WT baseline values with fallback logic: strict WT controls in the same generation → any controls in the same generation → any controls in the experiment. Raises `ValueError` if no controls are found |
| `_load_variant_measurements_for_generation(cur, experiment_id, generation)` | Loads averaged DNA and protein yields per variant, excludes control variants, filters missing measurements |
| `_load_generation_counts(cur, experiment_id, generation)` | Counts control and non-control variants for reporting and summary statistics |
| `_score_generation(cur, experiment_id, generation)` | Loads baseline values and variant measurements, computes activity scores, writes scores to database, tracks skipped variants, returns a summary |
| `calculate_scores_for_experiment(db, experiment_id, generation=None, commit=True, return_summary=False)` | Top-level entry point: loads generations, scores each, summarises statistics, commits to the database |

### References

| Source | Used for |
|---|---|
| Erhard F. (2018). *Estimating pseudocounts and fold changes for digital expression measurements.* Bioinformatics 34(23):4054–4063. [doi:10.1093/bioinformatics/bty471](https://doi.org/10.1093/bioinformatics/bty471) | Justification for `epsilon` as a pseudocount to prevent divide-by-zero errors and for log₂ transformation to produce symmetric, interpretable values |
| Leek J., Scharpf R., Bravo H. et al. (2010). *Tackling the widespread and critical impact of batch effects in high-throughput data.* Nat Rev Genet 11:733–739. [doi:10.1038/nrg2825](https://doi.org/10.1038/nrg2825) | Justification for the WT control fallback hierarchy — prioritising same-generation controls minimises the influence of batch effects |
