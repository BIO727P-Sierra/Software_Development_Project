from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from .db import get_db

bp = Blueprint("past_experiments", __name__, url_prefix="/experiments")


@bp.route("/")
@login_required
def list_experiments():
    """Show all saved experiments for the current user."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                experiment_id,
                experiment_name,
                uniprot_id,
                created_at,
                saved_at,
                (SELECT COUNT(*) FROM variants v WHERE v.experiment_id = e.experiment_id) AS variant_count
            FROM experiments e
            WHERE user_id = %s AND saved_at IS NOT NULL
            ORDER BY saved_at DESC
            """,
            (current_user.id,),
        )
        experiments = cur.fetchall()
    return render_template("experiments/past_experiments.html", experiments=experiments)


@bp.route("/save/<int:experiment_id>", methods=["POST"])
@login_required
def save_experiment(experiment_id):
    """Mark an experiment as saved (stamp saved_at timestamp)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM experiments WHERE experiment_id = %s",
            (experiment_id,),
        )
        row = cur.fetchone()

    if row is None or row["user_id"] != current_user.id:
        abort(403)

    with db.cursor() as cur:
        cur.execute(
            "UPDATE experiments SET saved_at = NOW() WHERE experiment_id = %s",
            (experiment_id,),
        )
    db.commit()
    flash("Experiment saved successfully!")

    # Redirect back to where the user came from, defaulting to results page
    next_url = request.form.get("next") or url_for(
        "analysis.results_experiment", experiment_id=experiment_id
    )
    return redirect(next_url)


@bp.route("/rename/<int:experiment_id>", methods=["POST"])
@login_required
def rename_experiment(experiment_id):
    """Rename an experiment."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM experiments WHERE experiment_id = %s",
            (experiment_id,),
        )
        row = cur.fetchone()

    if row is None or row["user_id"] != current_user.id:
        abort(403)

    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        flash("Experiment name cannot be empty.")
        return redirect(request.referrer or url_for("past_experiments.list_experiments"))

    if len(new_name) > 255:
        flash("Experiment name is too long (max 255 characters).")
        return redirect(request.referrer or url_for("past_experiments.list_experiments"))

    with db.cursor() as cur:
        cur.execute(
            "UPDATE experiments SET experiment_name = %s WHERE experiment_id = %s",
            (new_name, experiment_id),
        )
    db.commit()
    flash(f'Experiment renamed to "{new_name}".')
    return redirect(request.referrer or url_for("past_experiments.list_experiments"))


@bp.route("/delete/<int:experiment_id>", methods=["POST"])
@login_required
def delete_experiment(experiment_id):
    """Permanently delete an experiment and all its variants/measurements."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT user_id FROM experiments WHERE experiment_id = %s",
            (experiment_id,),
        )
        row = cur.fetchone()

    if row is None or row["user_id"] != current_user.id:
        abort(403)

    with db.cursor() as cur:
        cur.execute("DELETE FROM experiments WHERE experiment_id = %s", (experiment_id,))
    db.commit()
    flash("Experiment deleted.")
    return redirect(url_for("past_experiments.list_experiments"))
