def compute_activity_score(
    dna_yield,
    protein_yield,
    dna_baseline,
    protein_baseline,
    epsilon=1e-6,
    max_score=1_000_000.0,
):
    """
    Compute a unified Activity Score.

    Baseline-correct both DNA and protein yields, clamp negatives to 0,
    then score as corrected_dna / corrected_protein.
    """
    if dna_yield is None or protein_yield is None:
        raise ValueError("dna_yield and protein_yield must be present")

    corrected_dna = max(float(dna_yield) - float(dna_baseline), 0.0)
    corrected_protein = max(float(protein_yield) - float(protein_baseline), 0.0)

    score = corrected_dna / max(corrected_protein, epsilon)
    return min(score, max_score)


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


def _load_wt_baseline_for_generation(cur, experiment_id, generation):
    cur.execute(
        """
        SELECT
          AVG(m.dna_yield) AS dna_baseline,
          AVG(m.protein_yield) AS protein_baseline
        FROM measurements m
        JOIN variants v ON m.variant_id = v.variant_id
        JOIN experiments e ON v.experiment_id = e.experiment_id
        WHERE v.experiment_id = %s
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
    baseline = cur.fetchone()
    if baseline is None or baseline["dna_baseline"] is None or baseline["protein_baseline"] is None:
        raise ValueError(
            f"Missing WT control baseline for experiment {experiment_id}, generation {generation}"
        )
    return baseline["dna_baseline"], baseline["protein_baseline"]


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


def _score_generation(cur, experiment_id, generation):
    dna_baseline, protein_baseline = _load_wt_baseline_for_generation(cur, experiment_id, generation)
    variants = _load_variant_measurements_for_generation(cur, experiment_id, generation)

    for v in variants:
        score = compute_activity_score(
            dna_yield=v["dna_yield"],
            protein_yield=v["protein_yield"],
            dna_baseline=dna_baseline,
            protein_baseline=protein_baseline,
        )
        cur.execute(
            """
            UPDATE variants
            SET activity_score = %s
            WHERE variant_id = %s
            """,
            (score, v["variant_id"]),
        )
    return len(variants)


def calculate_scores_for_experiment(db, experiment_id, generation=None, commit=True):
    """
    Compute and persist Activity Scores for one experiment.

    If generation is None, score each generation independently using that
    generation's WT control baseline.
    """
    with db.cursor() as cur:
        generations = [generation] if generation is not None else _load_experiment_generations(cur, experiment_id)

        if not generations:
            return 0

        total_scored = 0
        for gen in generations:
            total_scored += _score_generation(cur, experiment_id, gen)

    if commit:
        db.commit()
    return total_scored
