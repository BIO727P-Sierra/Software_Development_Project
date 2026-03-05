from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired
from .uniprotAPI import retrieve_protein_sequence_features
from .db import get_db
import json

bp = Blueprint("uniprot", __name__, url_prefix="/uniprot")


class QueryForm(FlaskForm):
    uniprot_id = StringField("Enter UniProt ID:", validators=[InputRequired()])
    submit = SubmitField("Submit")


@bp.route("/", methods=("GET", "POST"))
@login_required
def uniprot_search():
    form = QueryForm()
    if form.validate_on_submit():
        uniprot_id = form.uniprot_id.data.strip()
        result = retrieve_protein_sequence_features(uniprot_id)
        if result[0] is not None:
            aminoacid_sequence, features_type_location = result
            session["uniprot_id"] = uniprot_id
            session["aminoacid_sequence"] = aminoacid_sequence
            session["features_type_location"] = features_type_location
            return redirect(url_for("uniprot.confirmation"))
        else:
            flash(result[1])
    return render_template("uniprot/uniprot_search.html", form=form)


@bp.route("/confirmation")
@login_required
def confirmation():
    uniprot_id = session.get("uniprot_id")
    aminoacid_sequence = session.get("aminoacid_sequence")
    features_type_location = session.get("features_type_location")
    return render_template(
        "uniprot/uniprot_review.html",
        uniprot_id=uniprot_id,
        aminoacid_sequence=aminoacid_sequence,
        features_type_location=features_type_location,
    )


@bp.route("/store", methods=("GET", "POST"))
@login_required
def data_stored():
    """
    Persist UniProt data + create an experiment row, then redirect to plasmid upload.
    Uses raw psycopg — no SQLAlchemy ORM needed.
    """
    uniprot_id = session.get("uniprot_id")
    aminoacid_sequence = session.get("aminoacid_sequence")
    features_type_location = session.get("features_type_location") or []

    if not uniprot_id or not aminoacid_sequence:
        flash("Session expired — please search again.")
        return redirect(url_for("uniprot.uniprot_search"))

    db = get_db()
    try:
        with db.cursor() as cur:
            # Create the experiment row (wt_dna_sequence left empty for now)
            cur.execute(
                """
                INSERT INTO experiments
                    (user_id, experiment_name, uniprot_id, wt_protein_sequence,
                     wt_dna_sequence, uniprot_features)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING experiment_id
                """,
                (
                    current_user.id,
                    f"Experiment – {uniprot_id}",
                    uniprot_id,
                    aminoacid_sequence,
                    "",               # wt_dna_sequence filled later via plasmid upload
                    json.dumps(features_type_location),
                ),
            )
            experiment_id = cur.fetchone()["experiment_id"]
        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Failed to save data: {e}")
        return redirect(url_for("uniprot.confirmation"))

    # Store experiment_id in session so subsequent steps can use it
    session["experiment_id"] = experiment_id
    session["validated"] = False   # plasmid not yet validated

    return redirect(url_for("FASTA_upload.plasmid_upload"))
