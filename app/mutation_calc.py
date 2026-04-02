# mutation_calc.py
# Detects and classifies mutations between a WT and variant protein using
# global pairwise alignment. Using alignment means a single indel is counted
# as one mutation rather than cascading mismatches at every downstream position.

from Bio.Align import PairwiseAligner


def run_mutation_analysis(
    *,
    wt_protein: str,
    variant_protein: str,
) -> dict:
    """
    Align variant protein to WT and identify mutations.

    Mutation types:
      - missense:  amino acid substitution (different residue, not stop)
      - nonsense:  substitution to a stop codon (*)
      - insertion: residue present in variant but absent in WT (gap in WT)
      - deletion:  residue present in WT but absent in variant (gap in variant)

    Returns:
      {
        "mutation_total": <int>,      total number of mutated positions
        "mutations": [                list of individual mutations
          {
            "position":       <int>,  1-based position in WT sequence
            "wt_residue":     <str>,  WT amino acid ("-" for insertions)
            "mutant_residue": <str>,  variant amino acid ("-" for deletions)
            "mutation_type":  <str>,  missense | nonsense | insertion | deletion
          },
          ...
        ]
      }
    """

    wt = (wt_protein or "").upper().strip()
    var = (variant_protein or "").upper().strip()

    if not wt or not var:
        return {"mutation_total": 0, "mutations": []}

    # ------------------------------------------------------------------
    # Alignment setup — same settings as sequence_processor.py so that
    # scoring behaviour is consistent across the pipeline
    # ------------------------------------------------------------------
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 1
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5

    try:
        aligner.max_number_of_alignments = 1  # prevents combinatorial explosion
    except Exception:
        pass  # older Biopython versions may not expose this attribute

    alignments = aligner.align(var, wt)
    it = iter(alignments)
    try:
        alignment = next(it)
    except StopIteration:
        return {"mutation_total": 0, "mutations": []}

    aligned_var, aligned_wt = alignment

    # ------------------------------------------------------------------
    # Walk alignment columns and classify each difference
    # ------------------------------------------------------------------
    mutations = []
    mutation_count = 0
    wt_pos = 0  # 0-based index into WT; incremented for every non-gap WT column

    for var_aa, wt_aa in zip(aligned_var, aligned_wt):

        # Advance WT position counter for every real WT residue
        if wt_aa != "-":
            wt_pos += 1

        # Exact match — no mutation
        if var_aa == wt_aa:
            continue

        mutation_count += 1

        if wt_aa == "-":
            # Gap in WT → insertion in variant
            mutations.append({
                "position": wt_pos,          # position after which the insertion falls
                "wt_residue": "-",
                "mutant_residue": var_aa,
                "mutation_type": "insertion",
            })

        elif var_aa == "-":
            # Gap in variant → deletion
            mutations.append({
                "position": wt_pos,
                "wt_residue": wt_aa,
                "mutant_residue": "-",
                "mutation_type": "deletion",
            })

        else:
            # Substitution — missense or nonsense
            mutation_type = "nonsense" if var_aa == "*" else "missense"
            mutations.append({
                "position": wt_pos,
                "wt_residue": wt_aa,
                "mutant_residue": var_aa,
                "mutation_type": mutation_type,
            })

    return {
        "mutation_total": mutation_count,
        "mutations": mutations,
    }
