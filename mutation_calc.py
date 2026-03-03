#mutation detecting and classifying function

def run_mutation_analysis(
        *,
        wt_protein: str,
        variant_protein: str,
        wt_dna: str,
        variant_dna: str,
) -> dict:
    
    #creating an empty list that will contain the mutation data
    mutations = []
    
    #creating a mutation counter
    mutation_count = 0

    # Ensuring the sequences are the same length
    codon_count = min(len(wt_dna), len(variant_dna)) // 3

    for i in range(codon_count):
        wt_codon = wt_dna[i*3:(i+3)*3]
        var_codon = variant_dna[i*3:(i+1)*3]

        if wt_codon != var_codon:

            mutation_count += 1

            wt_aa = wt_protein[i]
            var_aa = variant_protein[i]

            if var_aa == "*":
                mutation_type = "nonsense"
            elif wt_aa == var_aa:
                mutation_type = "synonymous"
            else:
                mutation_type = "misense" 

            mutations.append({
                "position":i+1,
                "wt_residue": wt_aa,
                "mutant_residue": var_aa,
                "mutation_type" : mutation_type,
            })
    
    return {
        "mutation_total":mutation_count,
        "mutations":mutations,
    }