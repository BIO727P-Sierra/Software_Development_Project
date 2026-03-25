# compute a unified activity score, where DNA and protein yields are baseline-corrected
# clamp yields to stay above 0 and then score as corrected_dna and corrected_protein
def compute_activity_score(
    dna_yield,
    protein_yield,
    dna_baseline,
    protein_baseline,
    epsilon=1e-6,
    max_score=1_000_000.0,
    min_protein=0.01,
):

    # Validate inputs and prevent divide by zero issues
    if dna_yield is None or protein_yield is None:
        raise ValueError("dna_yield and protein_yield must be present")

    corrected_dna = max(float(dna_yield) - float(dna_baseline), 0.0)
    corrected_protein = max(float(protein_yield) - float(protein_baseline), 0.0)

    if corrected_protein < min_protein:
        return None

    score = corrected_dna / max(corrected_protein, epsilon)
    return min(score, max_score)

# Find all unique generation numbers for an experiment and sort into ascending order
# return as a list
def _load_experiment_generations(cur, experiment_id):
    cur.execute(
        """
        SELECT DISTINCT generation
        FROM variants
        WHERE experiment_id = %s
        ORDER BY generation ASC
        """,
        (experiment_id,),
    )
    return [row["generation"] for row in cur.fetchall()]

# Run a SQL query to return WT control averages
# Returns if both are present, otherwise returns None
def _load_wt_baseline_for_generation(cur, experiment_id, generation):
    def _run_baseline_query(where_sql, params):
        cur.execute(
            f"""
            SELECT
              AVG(m.dna_yield) AS dna_baseline,
              AVG(m.protein_yield) AS protein_baseline
            FROM measurements m
            JOIN variants v ON m.variant_id = v.variant_id
            JOIN experiments e ON v.experiment_id = e.experiment_id
            WHERE {where_sql}
            """,
            params,
        )
        baseline = cur.fetchone()
        if baseline and baseline["dna_baseline"] is not None and baseline["protein_baseline"] is not None:
            return baseline["dna_baseline"], baseline["protein_baseline"]
        return None

    # Best-case baseline where strict WT controls in the same generation
    strict_same_generation = _run_baseline_query(
        """
        v.experiment_id = %s
        AND v.generation = %s
        AND m.is_control = TRUE
        AND (
          COALESCE(v.orf_protein_sequence, '') = e.wt_protein_sequence
          OR COALESCE(v.protein_sequence, '') = e.wt_protein_sequence
          OR v.plasmid_variant_index = 0
          OR LOWER(COALESCE(v.metadata->>'is_wt', 'false')) IN ('true', '1', 'yes')
        )
        """,
        (experiment_id, generation),
    )
    if strict_same_generation:
        return strict_same_generation

    # Fallback 1 if best-case doesn't work
    # any control in the same generation.
    any_control_same_generation = _run_baseline_query(
        """
        v.experiment_id = %s
        AND v.generation = %s
        AND m.is_control = TRUE
        """,
        (experiment_id, generation),
    )
    if any_control_same_generation:
        return any_control_same_generation

    # Final fallback for baselines
    # use any control samples in the experiment, otherwise raise an error
    any_control_experiment = _run_baseline_query(
        """
        v.experiment_id = %s
        AND m.is_control = TRUE
        """,
        (experiment_id,),
    )
    if any_control_experiment:
        return any_control_experiment

    raise ValueError(
        f"Missing control baseline for experiment {experiment_id}, generation {generation}"
    )

# Load per-variant measurement averages for one experiment and generation
# return as a list
def _load_variant_measurements_for_generation(cur, experiment_id, generation):
    cur.execute(
        """
        SELECT
          v.variant_id,
          AVG(m.dna_yield) AS dna_yield,
          AVG(m.protein_yield) AS protein_yield
        FROM variants v
        JOIN measurements m ON v.variant_id = m.variant_id
        WHERE v.experiment_id = %s
          AND v.generation = %s
          AND m.is_control = FALSE
          AND m.dna_yield IS NOT NULL
          AND m.protein_yield IS NOT NULL
        GROUP BY v.variant_id
        ORDER BY v.variant_id ASC
        """,
        (experiment_id, generation),
    )
    return cur.fetchall()

# Count how many variants are controls or non-controls in a generation
def _load_generation_counts(cur, experiment_id, generation):
    cur.execute(
        """
        SELECT
          COUNT(DISTINCT CASE WHEN m.is_control = FALSE THEN v.variant_id END) AS non_control_variants,
          COUNT(DISTINCT CASE WHEN m.is_control = TRUE THEN v.variant_id END) AS control_variants
        FROM variants v
        JOIN measurements m ON v.variant_id = m.variant_id
        WHERE v.experiment_id = %s
          AND v.generation = %s
        """,
        (experiment_id, generation),
    )
    row = cur.fetchone() or {}
    return {
        "non_control_variants": row.get("non_control_variants", 0) or 0,
        "control_variants": row.get("control_variants", 0) or 0,
    }

# Compute activity score with compute_activity_score and write into database if valid
# Counts how many were scored or skipped and returns a summary
def _score_generation(cur, experiment_id, generation):
    dna_baseline, protein_baseline = _load_wt_baseline_for_generation(cur, experiment_id, generation)
    counts = _load_generation_counts(cur, experiment_id, generation)
    variants = _load_variant_measurements_for_generation(cur, experiment_id, generation)

    scored_count = 0
    low_protein_skipped = 0
    for v in variants:
        score = compute_activity_score(
            dna_yield=v["dna_yield"],
            protein_yield=v["protein_yield"],
            dna_baseline=dna_baseline,
            protein_baseline=protein_baseline,
        )
        if score is not None:
            cur.execute(
                """
                UPDATE variants
                SET activity_score = %s
                WHERE variant_id = %s
                """,
                (score, v["variant_id"]),
            )
            scored_count += 1
        else:
            low_protein_skipped += 1

    return {
        "scored": scored_count,
        "controls_skipped": counts["control_variants"],
        "missing_measurement_skipped": max(counts["non_control_variants"] - len(variants), 0),
        "low_protein_skipped": low_protein_skipped,
    }

# Calculate activity scores for an experiment and commit into the database
def calculate_scores_for_experiment(db, experiment_id, generation=None, commit=True, return_summary=False):
    """
    Compute and persist Activity Scores for one experiment.

    If generation is None, score each generation independently using that
    generation's WT control baseline.
    """
    with db.cursor() as cur:
        generations = [generation] if generation is not None else _load_experiment_generations(cur, experiment_id)

        if not generations:
            summary = {
                "scored": 0,
                "controls_skipped": 0,
                "missing_measurement_skipped": 0,
                "low_protein_skipped": 0,
            }
            return summary if return_summary else 0

        summary = {
            "scored": 0,
            "controls_skipped": 0,
            "missing_measurement_skipped": 0,
            "low_protein_skipped": 0,
        }
        for gen in generations:
            gen_summary = _score_generation(cur, experiment_id, gen)
            summary["scored"] += gen_summary["scored"]
            summary["controls_skipped"] += gen_summary["controls_skipped"]
            summary["missing_measurement_skipped"] += gen_summary["missing_measurement_skipped"]
            summary["low_protein_skipped"] += gen_summary["low_protein_skipped"]

    if commit:
        db.commit()
    return summary if return_summary else summary["scored"]
