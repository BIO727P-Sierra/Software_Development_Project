# creating the data storing layer of our mutation function
def save_variant_mutations(db, variant_id: int, mutation_results: dict):
    """
    Store mutation analysis results in the database.
    """
    if "mutations" not in mutation_results:
        raise ValueError("mutation_results must include 'mutations'")

    mutations = mutation_results["mutations"] or []
    total = mutation_results.get("mutation_total", len(mutations))

    with db.cursor() as cur:
        # Remove previous mutation rows so they do not duplicate.
        cur.execute(
            "DELETE FROM mutations WHERE variant_id = %s",
            (variant_id,),
        )

        # Insert new mutation records.
        for m in mutations:
            cur.execute(
                """
                INSERT INTO mutations
                (variant_id, position, wt_residue, mutant_residue, mutation_type)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    variant_id,
                    m["position"],
                    m["wt_residue"],
                    m["mutant_residue"],
                    m["mutation_type"],
                ),
            )

        cur.execute(
            """
            UPDATE variants
            SET mutation_total = %s
            WHERE variant_id = %s
            """,
            (total, variant_id),
        )
