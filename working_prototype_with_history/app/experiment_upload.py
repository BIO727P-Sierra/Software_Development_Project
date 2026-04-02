from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from pathlib import Path

# Import python scripts
from .parse_data import parse_data
from .qc import validate_data
from .feedback import build_feedback, error_feedback
from .db import get_db

bp = Blueprint("experiment_upload", __name__, url_prefix="/experiment_upload")

# Upload directories for storage
EXPERIMENT_DATA_UPLOAD_DIR = Path("uploads/experiments")
EXPERIMENT_DATA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
experiment_ext = {"json", "tsv"}

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def insert_variants(db, experiment_id, valid_records):
    """Insert validated variant records into the database."""
    inserted = 0
    skipped = 0

    with db.cursor() as cur:
        for row in valid_records:
            try:
                cur.execute(
                    """
                    INSERT INTO variants (
                        experiment_id,
                        plasmid_variant_index,
                        parent_variant_id,
                        generation,
                        assembled_dna_sequence,
                        protein_sequence,
                        qc_passed
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING variant_id
                    """,
                    (
                        experiment_id,
                        int(row["plasmid_variant_index"]),
                        None,  # parent_variant_id resolved later
                        int(row["generation"]),
                        row["assembled_dna_sequence"],
                        row.get("protein_sequence") or "",  # NOT NULL in schema
                        True,
                    )
                )
                result = cur.fetchone()
                if result:
                    variant_id = result["variant_id"]
                    # Upsert measurements — delete-then-insert keeps it simple
                    # because measurements has no natural unique key of its own.
                    cur.execute(
                        "DELETE FROM measurements WHERE variant_id = %s",
                        (variant_id,),
                    )
                    # Insert measurements
                    cur.execute(
                        """
                        INSERT INTO measurements (
                            variant_id,
                            dna_yield,
                            protein_yield,
                            is_control
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (
                            variant_id,
                            float(row["dna_yield"]) if row.get("dna_yield") else None,
                            float(row["protein_yield"]) if row.get("protein_yield") else None,
                            _as_bool(row.get("is_control")),
                        )
                    )
                    inserted += 1
                else:
                    skipped += 1

            except Exception as e:
                skipped += 1
                continue

    db.commit()
    return inserted, skipped


# Upload page
@bp.route("/", methods=["GET", "POST"])
def experiment_upload():
    if not session.get("validated"):
        return redirect(url_for("FASTA_upload.plasmid_upload"))

    experiment_feedback = None
    experiment_id = session.get("experiment_id")

    if request.method == "POST":

        experiment_file = request.files.get("experiment_file")

        try:
            # Upload JSON or TSV
            if not experiment_file or experiment_file.filename == "":
                raise ValueError("No file detected.")

            filename = secure_filename(experiment_file.filename)
            file_path = EXPERIMENT_DATA_UPLOAD_DIR / filename
            experiment_file.save(file_path)

            parsed_data = parse_data(file_path)
            valid_records, rejected_records = validate_data(parsed_data)

            # Insert into DB
            db = get_db()
            inserted, skipped = insert_variants(db, experiment_id, valid_records)

            experiment_feedback = build_feedback(valid_records, rejected_records)
            experiment_feedback["inserted"] = inserted
            experiment_feedback["db_skipped"] = skipped

        except Exception as e:
            experiment_feedback = error_feedback(e)

    return render_template(
        "staging/experiment_upload.html",
        experiment_feedback=experiment_feedback,
        experiment_id=experiment_id,
    )
