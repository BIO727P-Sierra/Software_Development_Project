def fetch_top_performers(db, experiment_id, limit=10):
    """
    Display a table outlining the top 10 performing variants according to unified activity metric.

    Includes essential fields plus activity_score and mutation_total.
    """
    with db.cursor() as cur:

        cur.execute(
            """
            SELECT
              v.variant_id,
              v.generation,
              v.plasmid_variant_index,
              v.parent_variant_id,
              v.assembled_dna_sequence,
              AVG(m.dna_yield) AS dna_yield,
              AVG(m.protein_yield) AS protein_yield,
              v.activity_score,
              v.mutation_total
            FROM variants v
            LEFT JOIN measurements m ON m.variant_id = v.variant_id
            WHERE v.experiment_id = %s
              AND m.is_control = FALSE
              AND v.activity_score IS NOT NULL
            GROUP BY
              v.variant_id,
              v.generation,
              v.plasmid_variant_index,
              v.parent_variant_id,
              v.assembled_dna_sequence,
              v.activity_score,
              v.mutation_total
            ORDER BY v.activity_score DESC, v.variant_id ASC
            LIMIT %s
            """,
            (experiment_id, limit),
        )
        return cur.fetchall()
