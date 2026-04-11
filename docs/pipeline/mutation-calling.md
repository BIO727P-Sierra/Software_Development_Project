# Step 5: Mutation Calling

## What this step does

Following ORF detection, mutation calling is executed automatically for each variant that has a successfully identified ORF. The translated ORF protein sequence is aligned against the WT reference protein using global pairwise alignment, and every position where the two sequences differ is classified and recorded in the `mutations` table. The variant record is also updated with the total mutation count.

---

## For scientists

### Running mutation calling

Mutation calling is triggered automatically as part of the Analysis run — no additional user action is required. Results are visible in the experiment results table via the **Mutation Total** column and form the basis of the Mutation Fingerprint visualisation described in [Visualisations](visualisations.md).

### Interpreting mutation types

Each individual mutation is classified into one of four categories:

| Mutation type | Meaning |
|---|---|
| `missense` | WT and variant residues differ (both are standard amino acids) |
| `nonsense` | Variant residue is a stop codon (`*`), producing a truncated protein |
| `insertion` | Variant has a residue where the WT has a gap |
| `deletion` | WT has a residue where the variant has a gap |

!!! note "Silent mutations are not detected"
    Because the comparison operates at the protein level rather than the codon level, synonymous (silent) mutations — where the DNA codon changes but the encoded amino acid does not — are **not** detected by this function. Synonymous changes are invisible to protein-level alignment by definition.

---

## For developers

### Route

Mutation calling is triggered internally within the analysis route:

| Method | URL | Handler |
|---|---|---|
| `POST` | `/analysis/step1/run_experiment/<experiment_id>` | `analysis.run_step1_experiment` |

### Mutation calling logic

Mutation calling is implemented in `mutation_calc.py` via the `run_mutation_analysis()` function, which takes two keyword arguments: the WT protein sequence and the variant protein sequence identified by the ORF detection step. The variant protein is globally aligned against the WT protein using Biopython's `Bio.Align.PairwiseAligner` with the same scoring parameters as the ORF detection module, ensuring consistency across the pipeline.

```python title="mutation_calc.py — aligner configuration"
aligner = PairwiseAligner()
aligner.mode = "global"
aligner.match_score = 1
aligner.mismatch_score = -1
aligner.open_gap_score = -2
aligner.extend_gap_score = -0.5
```

The `max_number_of_alignments` parameter is set to `1` to prevent a pathological case where astronomically many equally optimal alignments cause memory overflow or excessive computation time. Only the single best alignment is retrieved.

### Walking the alignment

The aligned sequences are walked column by column. A WT position counter (`wt_pos`) is maintained separately and incremented only when a non-gap residue appears in the WT alignment row. This ensures that mutation positions are reported as correct 1-based indices into the WT sequence, even when insertions or deletions shift the alignment.

For each alignment column where the WT and variant residues differ, a mutation record is created and classified according to the following rules:

| Condition | Mutation type |
|---|---|
| Gap in WT, residue in variant | `insertion` |
| Gap in variant, residue in WT | `deletion` |
| Variant residue is a stop codon (`*`) | `nonsense` |
| Different amino acid (not stop, not gap) | `missense` |

### Return structure

The function returns a dictionary containing the total mutation count and a list of individual mutation records:

```python title="mutation_calc.py — return structure"
return {
    "mutation_total": mutation_count,
    "mutations": [
        {
            "position": wt_pos,          # 1-based position in WT
            "wt_residue": wt_aa,         # "-" for insertions
            "mutant_residue": var_aa,    # "-" for deletions
            "mutation_type": mutation_type,
        },
        ...
    ],
}
```

### Database write

Mutation results are persisted by `save_variant_mutations()` in `mutation_repository.py`. The function first **deletes** any existing mutation rows for the variant to prevent duplication on re-runs, then inserts one row per mutation into the `mutations` table, and finally updates the `mutation_total` column on the variants row:

```sql
DELETE FROM mutations WHERE variant_id = %s;

INSERT INTO mutations (variant_id, position, wt_residue, mutant_residue, mutation_type)
VALUES (%s, %s, %s, %s, %s);

-- Update total count on the variant
UPDATE variants SET mutation_total = %s WHERE variant_id = %s;
```

### Integration with the analysis pipeline

Mutation calling is invoked within the analysis loop in `analysis.py`, immediately after a successful ORF result is written to the database. It is only executed for variants where `step1_status = 'ok'`, ensuring that variants with failed ORF detection are skipped.

### Error handling

| Condition | Behaviour |
|---|---|
| Variant has `step1_status = 'error'` | Mutation calling skipped entirely for that variant |
| Either protein sequence is empty or `None` | Function returns `{"mutation_total": 0, "mutations": []}` |
| No alignment produced (`StopIteration`) | Function returns `{"mutation_total": 0, "mutations": []}` |
| Sequences differ in length | Handled by global alignment via gap penalties; no error raised |
