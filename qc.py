qc_fields = [
    "plasmid_variant_index",
    "assembled_dna_sequence",
    "generation",
    "dna_yield"
]

def validate_data(records):
    # Data that has gone through QC is validated

    valid = []
    rejected = []

    for row in records:
        missing_data = [
            f for f in qc_fields 
            if row.get(f) is None or row.get(f) == ""
            ]

        if missing_data:
            rejected.append({ 
                "record": row,
                "reason": f"Missing data: {missing_data}"
            })
            continue

        if row["dna_yield"] is None:
            rejected.append({
                "record": row,
                "reason": "Invalid numeric dna_yield"
            })
            continue
            
        valid.append(row)
    
    return valid, rejected