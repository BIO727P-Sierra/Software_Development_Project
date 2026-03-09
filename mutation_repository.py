#creating the data storing layer of our mutation function
def save_variant_mutations(db, variant_id: int, mutation_results: dict):
    """
    This stores the mutation analysis results in the database.
    """

    mutations = mutation_results["mutations"]
    total = mutation_results["mutation_total"]

    with db.cursor() as cur:
        
        #remove previous mutation rows so they don't show up as duplicates.

        cur.execute(
            "DELETE FROM mutations WHERE variant_id = %s",
            (variant_id,),
        )

        #inserting the new mutation records
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

            #execute mutation_total in variants table

        cur.execute(
             """
            UPDATE variants
            SET mutation_total = %s
            WHERE variant_id = %s
            """,
            (total, variant_id),
        )