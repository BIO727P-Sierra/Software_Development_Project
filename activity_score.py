# Import database connection helper from db.py
# get_db to interact with the PostgreSQL database
from .db import get_db

# Define function parameters
def compute_activity_score(dna_yield, protein_yield, dna_baseline, protein_baseline, epsilon=1e-6):
    """
    Compute unified Activity Score for a variant.
    DNA yield is normalized against protein yield, using WT as baselines.
    """
    corrected_dna = dna_yield - dna_baseline
    corrected_protein = protein_yield - protein_baseline
    return corrected_dna / (corrected_protein + epsilon) # epsilon to avoid dividing by zero (prevent crashing)


def calculate_scores_for_experiment(db, experiment_id, generation=None):
    """
    Compute activity scores for all variants in an experiment (optionally filtered by generation).
    Updates the variants.activity_score column.
    """
    with db.cursor() as cur:

        # Fetch WT measurements for baseline calculation
        wt_query = """
            SELECT AVG(dna_yield) AS dna_baseline,
                   AVG(protein_yield) AS protein_baseline
            FROM measurements m
            JOIN variants v ON m.variant_id = v.variant_id
            WHERE v.experiment_id = %s AND m.is_control = TRUE
        """
        params = [experiment_id]

        if generation is not None:
            wt_query += " AND v.generation = %s"
            params.append(generation)

        cur.execute(wt_query, params)
        baseline = cur.fetchone()

        if baseline is None or baseline["dna_baseline"] is None or baseline["protein_baseline"] is None:
            raise ValueError("No WT control measurements found for this experiment/generation")

        dna_baseline = baseline["dna_baseline"]
        protein_baseline = baseline["protein_baseline"]

        # Fetch all variant measurements (excluding controls)
        variant_query = """
            SELECT v.variant_id, AVG(m.dna_yield) AS dna_yield, AVG(m.protein_yield) AS protein_yield
            FROM variants v
            JOIN measurements m ON v.variant_id = m.variant_id
            WHERE v.experiment_id = %s AND m.is_control = FALSE
        """
        params = [experiment_id]

        if generation is not None:
            variant_query += " AND v.generation = %s"
            params.append(generation)

        variant_query += " GROUP BY v.variant_id ORDER BY v.variant_id ASC"

        cur.execute(variant_query, params)
        variants = cur.fetchall()

        # Compute and write Activity Scores
        for v in variants:
            score = compute_activity_score(
                dna_yield=v["dna_yield"],
                protein_yield=v["protein_yield"],
                dna_baseline=dna_baseline,
                protein_baseline=protein_baseline
            )
            cur.execute(
                """
                UPDATE variants
                SET activity_score = %s
                WHERE variant_id = %s
                """,
                (score, v["variant_id"])
            )

    db.commit()
    return len(variants)