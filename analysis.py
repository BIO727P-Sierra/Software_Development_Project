# analysis.py
from flask import Blueprint, render_template, redirect, url_for, flash, abort, session
from .db import get_db
from .sequence_processor import run_step1_for_variant_row, SelectionPolicy

bp = Blueprint("analysis", __name__, url_prefix="/analysis")


#added imports needed for the mutation step 
from .mutation_calc import run_mutation_analysis

from .mutation_repository import save_variant_mutations
from .activity_score import calculate_scores_for_experiment
from .top_performer_table import fetch_top_performers


# -----------------------------
# Results (ONE page per experiment) ##Addition -- adding mutation total add the end of the query    
# -----------------------------
@bp.route("/results/experiment/<int:experiment_id>", methods=("GET",))
def results_experiment(experiment_id: int):
    """
    Results page for an experiment: shows Step 1 ORF outputs
    for all variants under that experiment.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT experiment_id, experiment_name, uniprot_id
            FROM experiments
            WHERE experiment_id = %s
            """,
            (experiment_id,),
        )
        exp = cur.fetchone()

        if exp is None:
            abort(404)

        cur.execute(
            """
            SELECT
              v.variant_id,
              v.generation,
              v.plasmid_variant_index,
              v.parent_variant_id,
              v.step1_status,
              v.step1_error,
              v.orf_start,
              v.orf_end,
              v.orf_strand,
              v.orf_frame,
              v.orf_score,
              v.orf_coverage,
              v.orf_final,
              v.orf_protein_len,
              v.orf_cds_dna,
              v.orf_protein_sequence,
              v.mutation_total
            FROM variants v
            WHERE v.experiment_id = %s
            ORDER BY v.plasmid_variant_index ASC NULLS LAST
            """,
            (experiment_id,),
        )
        rows = cur.fetchall()

    return render_template("analysis/results.html", exp=exp, rows=rows)


@bp.route("/results/experiment/<int:experiment_id>/top-performers", methods=("GET",))
def top_performers(experiment_id: int):
    """
    Top performers table for an experiment based on activity_score.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT experiment_id, experiment_name, uniprot_id
            FROM experiments
            WHERE experiment_id = %s
            """,
            (experiment_id,),
        )
        exp = cur.fetchone()

        if exp is None:
            abort(404)

    rows = fetch_top_performers(db, experiment_id, limit=10)
    summary = session.get("analysis_summary")
    return render_template("analysis/top_performers.html", exp=exp, rows=rows, summary=summary)


# -----------------------------
# Step 1 — whole experiment
# -----------------------------
@bp.route("/step1/run_experiment/<int:experiment_id>", methods=("POST",))
def run_step1_experiment(experiment_id: int):
    """
    Run Step 1 for ALL variants in an experiment.
    Writes ORF results back to SQL for each variant, then redirects to results page.
    """
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT wt_protein_sequence, wt_dna_sequence
            FROM experiments
            WHERE experiment_id = %s
            """,
            (experiment_id,),
        )
        exp_row = cur.fetchone()

    if exp_row is None:
        flash("Experiment not found.")
        return redirect(url_for("home.index"))

    wt_protein = exp_row["wt_protein_sequence"]
    
    #new addition
    wt_dna = exp_row["wt_dna_sequence"]
    
    if not wt_protein:
        flash("Staging not complete: missing WT protein sequence.")
        return redirect(url_for("analysis.results_experiment", experiment_id=experiment_id))

    if not wt_dna:
        flash("Staging not complete: missing WT DNA sequence.")
        return redirect(url_for("analysis.results_experiment", experiment_id=experiment_id))

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT variant_id, assembled_dna_sequence
            FROM variants
            WHERE experiment_id = %s
            ORDER BY plasmid_variant_index ASC NULLS LAST
            """,
            (experiment_id,),
        )
        variants = cur.fetchall()

    if not variants:
        flash("No variants found for this experiment.")
        return redirect(url_for("analysis.results_experiment", experiment_id=experiment_id))

    policy = SelectionPolicy()

    for v in variants:
#STEP 1 ORF detection
        out = _run_step1_safe(
            wt_protein,
            v["assembled_dna_sequence"],
            policy=policy
        )

        _write_step1_result(db, v["variant_id"], out)

    #step 2 mutation
        if out["step1_status"] == "ok":
        
            mutation_results = run_mutation_analysis(
                wt_protein=wt_protein,
                variant_protein=out["orf_protein_sequence"],
                wt_dna=wt_dna,
                variant_dna=out["orf_cds_dna"]
            )
            save_variant_mutations(
                db,
                v["variant_id"],
                mutation_results
            )

       
    db.commit()

    try:
        score_summary = calculate_scores_for_experiment(db, experiment_id, return_summary=True)
        session["analysis_summary"] = {
            "processed": len(variants),
            "scored": score_summary["scored"],
            "controls_skipped": score_summary["controls_skipped"],
            "missing_measurements_skipped": score_summary["missing_measurement_skipped"],
            "low_protein_skipped": score_summary.get("low_protein_skipped", 0),
        }
    except ValueError as e:
        session["analysis_summary"] = {
            "processed": len(variants),
            "error": str(e),
        }

    return redirect(url_for("analysis.results_experiment", experiment_id=experiment_id))


# -----------------------------
# Internal helpers
# -----------------------------

def _run_step1_safe(wt_protein: str, assembled_dna: str, policy: SelectionPolicy = None) -> dict:
    """
    Run Step 1 with full error handling. Always returns a dict ready for DB write.
    Never raises — failures are captured as step1_status = 'error'.
    """
    if not assembled_dna:
        return _error_out("Missing assembled DNA sequence.")

    try:
        result = run_step1_for_variant_row(
            wt_protein_sequence=wt_protein,
            assembled_dna_sequence=assembled_dna,
            policy=policy or SelectionPolicy(),
        )
        return result
    except Exception as e:
        return _error_out(str(e))


def _error_out(message: str) -> dict:
    """Return a Step 1 error result dict with all ORF fields set to None."""
    return {
        "step1_status": "error",
        "step1_error": message,
        "orf_start": None,
        "orf_end": None,
        "orf_strand": None,
        "orf_frame": None,
        "orf_score": None,
        "orf_coverage": None,
        "orf_final": None,
        "orf_protein_len": None,
        "orf_cds_dna": None,
        "orf_protein_sequence": None,
    }


def _write_step1_result(db, variant_id: int, out: dict) -> None:
    """Write Step 1 results dict to the variants table."""
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE variants
            SET
              step1_status       = %(step1_status)s,
              step1_error        = %(step1_error)s,
              orf_start          = %(orf_start)s,
              orf_end            = %(orf_end)s,
              orf_strand         = %(orf_strand)s,
              orf_frame          = %(orf_frame)s,
              orf_score          = %(orf_score)s,
              orf_coverage       = %(orf_coverage)s,
              orf_final          = %(orf_final)s,
              orf_protein_len    = %(orf_protein_len)s,
              orf_cds_dna        = %(orf_cds_dna)s,
              orf_protein_sequence = %(orf_protein_sequence)s
            WHERE variant_id = %(variant_id)s
            """,
            {**out, "variant_id": variant_id},
        )
        

