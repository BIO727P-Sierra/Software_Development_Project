"""
sequence_processor.py

Step 1 (Analysis pipeline):
Identify the target coding ORF in a circular plasmid by matching candidate ORF
proteins to a WT reference protein sequence.
Integration with Flask/SQL is done via small adapter functions run_step1_for_variant_row()
that accept WT protein + variant plasmid DNA that
SQL data layer already stores (experiments.wt_protein_sequence,
variants.assembled_dna_sequence).
"""

# -----------------------------
# Packages
# -----------------------------

# Enables forward type hints (cleaner typing) without runtime import issues
from __future__ import annotations


from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# Biopython provides reverse-complement + translation
from Bio.Seq import Seq

# Alignment API; used for Step 1 scoring (can be replaceable without changing call signature)
# Uses modern Bio.Align.PairwiseAligner (replaces deprecated Bio.pairwise2)
from Bio.Align import PairwiseAligner

# -----------------------------
# Data structures
# -----------------------------

@dataclass
class ORFHit:
    """Identified open reading frame (candidate CDS)."""
    cds_dna: str        # storing the CDS DNA allows re-translation/re-alignment without rescanning ORFs (optional to record in DB)
    protein: str        # protein is used for scoring vs WT; protein-level matching is robust to synonymous DNA changes
    start: int          # Stores the 0-based start coordinate of the ORF within the circular plasmid (circular indexing)
    end: int            # Stores the 0-based end coordinate of the ORF within the circular plasmid (circular indexing)
    strand: str         # Records whether the ORF lies on '+' or '-', forward vs reverse-complement strand
    frame: int          # Stores the codon frame used for translation, e.g. frame=1 codons start at (start+1) - frame-shift
    score: float = 0.0  # score = 1.0 = 100% identity vs WT protein = every aligned residue matched
    coverage: float = 0.0  # coverage = 1.0 = full-length match (prevents selecting short ORFs that match a small fragment well)
    final: float = 0.0  # combined score used for selection (final = score × coverage)

@dataclass(frozen=True)
class SelectionPolicy:
    """Thresholds/Filter used to select the best ORF."""
    min_aa: int = 200 # ignores tiny ORFs that are unlikely to be polymerase
    coverage_threshold: float = 0.8  # enforces that candidate aligns to a majority of WT
    score_threshold: float = 0.5  # minimum alignment identity; below this the wrong gene was almost certainly picked
    length_window: Tuple[float, float] = (0.85, 1.15) # plausible length bounds relative to WT; filters truncations/concatemers

# allows swapping scoring method without changing core code
Scorer = Callable[[str, str], Tuple[float, float]] 


# -----------------------------
# Orchestrator class
# -----------------------------

class SequenceProcessor:
    """Orchestrates Step 1 (ORF discovery → scoring → selection)."""

    # Binds the wild-type protein to the processor once per experiment,
    # avoids repeatedly passing WT protein into every internal function
    def __init__(self, wt_protein_sequence: str):
        # normalise input to avoid case/whitespace bugs or pass empty 
        self.wt_protein = (wt_protein_sequence or "").upper().strip()
        if not self.wt_protein: # fail fast if empty
            raise ValueError("WT protein sequence is empty")

    ###ORFHit###
    def find_target_orf_in_plasmid(
        self,
        plasmid_dna: str,
        *,
        policy: SelectionPolicy = SelectionPolicy(),
        scorer: Scorer = None,
    ) -> ORFHit:
        """
        Identify the correct coding ORF within a circular plasmid by comparison to a
        WT protein reference
        """
        # -----------------------------
        # Input normalisation
        # -----------------------------
        
        dna = _normalise_dna(plasmid_dna)
        
        # -----------------------------
        # Circular plasmid handling
        # -----------------------------
        
        # Plasmids are circular, so coding regions may span the origin.
        # We extend the sequence by duplicating a limited prefix so that
        # ORFs crossing the boundary are still detectable in linear scanning.
        # The wrap length is bounded by:
        # - the plasmid length (upper bound)
        # - an estimate based on WT protein length (3 bases per amino acid + buffer)
        # This avoids unnecessary scanning of excessively long duplicated sequences.    
        
        wrap_bases = min(len(dna), len(self.wt_protein) * 3 + 300)
        
        # -----------------------------
        # ORF discovery
        # -----------------------------

        # Identify all candidate ORFs on both strands and all three reading frames.
        # At this stage, ORFs are filtered only by minimum length; no WT comparison
        # occurs yet, keeping discovery independent of scoring heuristics.

        hits = discover_orfs_circular(dna,
                                      min_aa=policy.min_aa,
                                      wrap_bases=wrap_bases)
        
        # If no ORFs pass the basic length filter fail early
        if not hits:
            raise ValueError("No ORFs found in plasmid")
            
        # -----------------------------
        # Scoring configuration
        # ----------------------------- 
        
        if scorer is None:
            scorer = default_protein_scorer

        # -----------------------------
        # ORF scoring
        # -----------------------------

        # Compare each candidate ORF protein to the WT protein reference.
        # This assigns:
        # - identity-based score (similarity)
        # - coverage (fraction of WT aligned)
        #
        # These metrics are used to distinguish the true coding ORF from
        # spurious ORFs of similar length or partial matches.

        scored = score_orfs(hits,
                            wt_protein=self.wt_protein,
                            scorer=scorer
                           )
        
        # -----------------------------
        # ORF selection
        # -----------------------------

        # Apply biologically motivated selection criteria:
        # - length plausibility relative to WT
        # - minimum coverage threshold
        # - ranking by coverage and combined score
        # The result is a single, unambiguous ORF representing the coding
        # sequence of this plasmid variant.
        
        return select_best_orf(scored,
                               wt_len=len(self.wt_protein),
                               policy=policy
                              )


# ============================================================
# SequenceProcessor (Orchestrator class) — END
# Helper functions (internal) — START
# ============================================================

# -----------------------------
# ORF discovery (circular + both strands)
# -----------------------------


def discover_orfs_circular(dna: str, *, min_aa: int, wrap_bases: int) -> List[ORFHit]:
    """
    Find ORFs on both strands with circular wrap-around.
    
    Implements the circular plasmid extension approach: duplicates a portion
    of the sequence at the end so origin-crossing ORFs appear as continuous
    regions in linear scanning. This is the standard pattern used by prokaryotic
    gene finders like Prodigal/Pyrodigal.
    """
    
    dna = _normalise_dna(dna)  # consistent DNA format and early erroring
    n = len(dna)  # original plasmid length before extension
    wrap_bases = max(1, min(n, wrap_bases))  # prevent zero wrap and avoid wrapping longer than plasmid

    extended = dna + dna[:wrap_bases]  # creates a linear window that includes origin-crossing ORFs

    hits: List[ORFHit] = []  # collect candidate ORFs before scoring; separation keeps discovery independent of WT
    hits.extend(_find_orfs_in_seq(extended, orig_len=n, strand="+", min_aa=min_aa))  # forward strand ORFs are valid candidates

    rc = str(Seq(extended).reverse_complement())  # reverse complement is required to search coding regions on the opposite strand
    hits.extend(_find_orfs_in_seq(rc, orig_len=n, strand="-", min_aa=min_aa))  # scan reverse strand using same logic

    return hits  # return all candidates; selection happens later using WT protein similarity


def _find_orfs_in_seq(seq: str, *, orig_len: int, strand: str, min_aa: int) -> List[ORFHit]:
    """
    Find ORFs in a single linear sequence (one strand, extended for circular handling).
    
    Scans all three reading frames and identifies ORFs as regions starting with
    methionine (M) and ending with stop codon (*). This follows the Biostars
    community pattern which is more robust than the Biopython cookbook's
    simplistic stop-to-stop approach.
    """
    hits: List[ORFHit] = []
    seq_obj = Seq(seq)

    # Scan all three possible reading frames (0, 1, 2)
    for frame in range(3):
        sub = seq_obj[frame:]  # shift by frame offset
        sub = sub[: (len(sub) // 3) * 3]  # trim to full codons (multiple of 3)
        protein = str(sub.translate(to_stop=False))  # translate entire sequence including stops

        # Scan translated protein for ORFs (M...*)
        i = 0
        while i < len(protein):
            start_idx = protein.find("M", i)  # find next methionine (start codon)
            if start_idx == -1:  # no more start codons in this frame
                break

            stop_idx = protein.find("*", start_idx + 1)  # find stop codon after start
            if stop_idx == -1:  # no stop codon found (incomplete ORF)
                i = start_idx + 1  # skip this M and continue searching
                continue

            orf_protein = protein[start_idx:stop_idx]  # extract ORF protein (M to stop, exclusive of *)
            if len(orf_protein) >= min_aa:  # only keep ORFs meeting minimum length threshold
                # Map protein coordinates back to DNA coordinates
                dna_start = frame + start_idx * 3  # DNA position of start codon
                dna_end = frame + stop_idx * 3  # DNA position of stop codon
                cds_dna = seq[dna_start:dna_end]  # extract CDS DNA sequence

                # Map extended/linear coordinates back to circular coordinates
                start0, end0 = _map_coords(dna_start, dna_end, orig_len, strand)

                hits.append(
                    ORFHit(
                        cds_dna=cds_dna,
                        protein=orf_protein,
                        start=start0,
                        end=end0,
                        strand=strand,
                        frame=frame,
                    )
                )

            i = stop_idx + 1  # continue searching after this stop codon

    return hits


def _map_coords(start: int, end: int, orig_len: int, strand: str) -> Tuple[int, int]:
    """
    Map linear/extended coordinates back to circular plasmid coordinates.
    
    For forward strand: simple modulo arithmetic wraps coordinates to circular space
    For reverse strand: additionally flip coordinates since RC reverses the sequence
    """
    if strand == "+":
        # Forward strand: just wrap using modulo
        return start % orig_len, end % orig_len
    
    # Reverse strand: flip coordinates (sequence is reversed)
    # The end in the extended sequence maps to start in circular space
    s = (orig_len - (end % orig_len)) % orig_len
    e = (orig_len - (start % orig_len)) % orig_len
    return s, e


def _normalise_dna(dna: str) -> str:
    """
    Normalize DNA sequence input: uppercase and strip whitespace.
    Validates that sequence is not empty to fail fast.
    """
    d = (dna or "").upper().strip()
    if not d:
        raise ValueError("Plasmid DNA sequence is empty")
    return d


# -----------------------------
# Protein alignment and scoring
# -----------------------------

def default_protein_scorer(query_protein: str, wt_protein: str) -> Tuple[float, float]:
    """
    Score a candidate ORF protein against the WT reference using global alignment.

    Returns:
      (score_norm, coverage)

    Where:
      - score_norm = (# exact matches in aligned positions) / (WT length)
        This behaves like a WT-normalised identity: 1.0 means every WT residue matched.

      - coverage = (# aligned non-gap positions) / (WT length)
        This tells you how much of the WT is covered by the alignment, preventing short
        ORFs from “looking good” by matching only a small fragment.

    Notes:
      - Uses Bio.Align.PairwiseAligner (modern Biopython API).
      - Forces a single best alignment to avoid a pathological case where there are
        astronomically many equally-optimal alignments (which can overflow).
    """
    # -----------------------------
    # Input normalisation
    # -----------------------------
    wt = (wt_protein or "").upper().strip()
    q = (query_protein or "").upper().strip()

    # Fail fast on empty inputs (keeps downstream code simple and safe)
    if not wt or not q:
        return 0.0, 0.0

    # -----------------------------
    # Aligner configuration
    # -----------------------------
    # Global alignment makes "coverage" meaningful because it aligns end-to-end
    # (with gaps allowed), rather than only aligning a best local region.
    aligner = PairwiseAligner()
    aligner.mode = "global"

    # Scoring scheme (same intent as your old pairwise2 settings)
    aligner.match_score = 1
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5

    # -----------------------------
    # Critical safety: avoid explosion of equally-optimal alignments
    # -----------------------------
    # Some sequences / scoring schemes produce a huge number of optimal alignments.
    # Biopython may attempt to count them, which can overflow a 64-bit integer
    # or become extremely slow. We only need the *best* one.
    try:
        aligner.max_number_of_alignments = 1
    except Exception:
        # Older Biopython versions may not expose this; safe to ignore
        pass

    # Compute alignments (this returns an iterable-like object)
    alignments = aligner.align(q, wt)

    # IMPORTANT: do NOT do len(alignments) here.
    # In the pathological case, computing the number of optimal alignments can
    # overflow (this is the error you saw in the UI).
    it = iter(alignments)
    try:
        alignment = next(it)  # take the single best alignment
    except StopIteration:
        return 0.0, 0.0

    # In your current setup this unpacking is working (you already get "ok" results).
    # It yields the aligned (gapped) strings used below for counting.
    aligned_query, aligned_wt = alignment

    # -----------------------------
    # Metric calculation (WT-normalised)
    # -----------------------------
    wt_len = len(wt)

    # Coverage: count aligned residue pairs (ignore gaps on either side),
    # then normalise by WT length.
    aligned = sum(
        1 for cq, cw in zip(aligned_query, aligned_wt)
        if cw != "-" and cq != "-"
    )
    coverage = aligned / max(1, wt_len)

    # Identity score: count exact matches at aligned (non-gap) positions,
    # then normalise by WT length.
    matches = sum(
        1 for cq, cw in zip(aligned_query, aligned_wt)
        if cw != "-" and cq != "-" and cq == cw
    )
    score_norm = matches / max(1, wt_len)

    return score_norm, coverage


def score_orfs(orfs: List[ORFHit], *, wt_protein: str, scorer: Scorer) -> List[ORFHit]:
    """
    Score all candidate ORFs by aligning their proteins against WT reference.
    
    For each ORF, calculates:
    - score: alignment identity (from scorer)
    - coverage: alignment coverage (from scorer)
    - final: combined metric incorporating length similarity
    
    The final score penalizes ORFs with very different lengths from WT,
    which helps filter out truncations, extensions, and concatemers.
    """
    wt = (wt_protein or "").upper().strip()
    if not wt:
        raise ValueError("WT protein sequence is empty")

    wt_len = len(wt)

    for h in orfs:
        # Get alignment-based metrics from scorer
        s, cov = scorer(h.protein, wt)
        
        # Penalize ORFs with very different lengths from WT
        # length_similarity = 1.0 means same length as WT
        # length_similarity → 0.0 as length difference increases
        length_similarity = max(0.0, 1.0 - (abs(len(h.protein) - wt_len) / max(1, wt_len)))
        
        # Store metrics in ORFHit object (mutating in place)
        h.score = s  # alignment identity
        h.coverage = cov  # alignment coverage
        h.final = s * length_similarity  # combined score for ranking

    return orfs


# -----------------------------
# ORF selection and filtering
# -----------------------------


def select_best_orf(scored_orfs: List[ORFHit], *, wt_len: int, policy: SelectionPolicy) -> ORFHit:
    """
    Select the single best ORF from scored candidates using biological filters.
    
    Applies multi-stage filtering:
    1. Length plausibility: ORF must be within acceptable range of WT length
    2. Coverage threshold: ORF must align to sufficient fraction of WT
    3. Ranking: pick ORF with best coverage, breaking ties with final score
    
    Raises ValueError if no candidates pass filters or best candidate is below threshold.
    """
    # Calculate acceptable length bounds based on WT and policy
    lo = int(policy.length_window[0] * wt_len)  # minimum acceptable length (e.g., 70% of WT)
    hi = int(policy.length_window[1] * wt_len)  # maximum acceptable length (e.g., 130% of WT)

    # Filter candidates by length plausibility
    candidates = [h for h in scored_orfs if lo <= len(h.protein) <= hi]
    if not candidates:
        raise ValueError(
            "No ORF candidates passed length_window filtering; widen length_window or lower min_aa."
        )

    # Rank by final score (primary: score × length_similarity) then coverage (tiebreaker)
    # final is preferred as primary because it rewards both high identity and correct length
    best = max(candidates, key=lambda h: (h.final, h.coverage))

    # Validate that best candidate meets minimum coverage threshold
    if best.coverage < policy.coverage_threshold:
        raise ValueError(
            f"Best ORF coverage {best.coverage:.2f} < threshold {policy.coverage_threshold:.2f}."
        )

    # Validate that best candidate meets minimum score threshold
    if best.score < policy.score_threshold:
        raise ValueError(
            f"Best ORF score {best.score:.2f} < threshold {policy.score_threshold:.2f}."
        )

    return best


# -----------------------------
# Utility functions
# -----------------------------


def extract_circular_region(dna: str, start: int, end: int) -> str:
    """
    Extract a region from circular DNA using (start,end) coords.
    
    Handles both normal regions (start < end) and wrap-around regions (start > end).
    Uses modulo arithmetic to handle circular coordinates correctly.
    """
    dna = _normalise_dna(dna)
    n = len(dna)
    start %= n  # wrap to valid circular coordinates
    end %= n
    
    if start == end:  # zero-length region
        return ""
    
    if start < end:  # normal region (no wrap-around)
        return dna[start:end]
    
    # Wrap-around region (crosses origin)
    return dna[start:] + dna[:end]


# -----------------------------
# Flask / SQL integration adapter
# -----------------------------


def run_step1_for_variant_row(
    *,
    wt_protein_sequence: str,
    assembled_dna_sequence: str,
    policy: SelectionPolicy = SelectionPolicy(),
) -> Dict[str, Any]:
    """
    Adapter for SQL/Flask: returns a dict ready to UPDATE the variants table.
    
    This is the main entry point for running Step 1 on a single variant row.
    Takes inputs that SQL already has (wt_protein, variant DNA) and returns
    a dict with all the fields needed to update the variants table in one go.
    """
    processor = SequenceProcessor(wt_protein_sequence)  # bind WT protein once
    best = processor.find_target_orf_in_plasmid(assembled_dna_sequence, policy=policy)  # find target ORF
    return results_to_variant_update(best, status="ok", error=None)  # format results for DB update


def results_to_variant_update(best: ORFHit, *, status: str, error: Optional[str]) -> Dict[str, Any]:
    """
    Standard Step-1 output fields to persist in SQL.
    
    Converts ORFHit object to flat dict with column names matching the SQL schema.
    Includes status/error tracking for pipeline monitoring.
    """
    return {
        "step1_status": status,  # "ok" or "failed"
        "step1_error": error,  # error message if failed, None if ok
        "orf_start": int(best.start),  # 0-based start coordinate (circular)
        "orf_end": int(best.end),  # 0-based end coordinate (circular)
        "orf_strand": best.strand,  # '+' or '-'
        "orf_frame": int(best.frame),  # reading frame (0, 1, or 2)
        "orf_score": float(best.score),  # alignment identity score
        "orf_coverage": float(best.coverage),  # alignment coverage
        "orf_final": float(best.final),  # combined selection score
        "orf_protein_len": int(len(best.protein)),  # length of translated protein
        "orf_cds_dna": best.cds_dna,  # coding DNA sequence
        "orf_protein_sequence": best.protein, # translated ORF protein need it later for: mutation calling
    }

