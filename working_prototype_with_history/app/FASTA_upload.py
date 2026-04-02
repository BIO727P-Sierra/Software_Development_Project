import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
from pathlib import Path

from .FASTA_parsing_logic import parse_file as parse_fasta, validate_protein
from .db import get_db

bp = Blueprint("FASTA_upload", __name__, url_prefix="/plasmid_upload")

PLASMID_UPLOAD_DIR = Path("uploads/plasmids")
PLASMID_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FASTA_EXTENSIONS = {"fasta", "fa", "fna"}


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


@bp.route("/", methods=("GET", "POST"))
@login_required
def plasmid_upload():
    validation_result = None
    experiment_id = session.get("experiment_id")

    # Fetch uniprot_id for display in the template
    uniprot_id = session.get("uniprot_id", "")

    if request.method == "POST":
        fasta_file = request.files.get("fasta_file")
        try:
            if not experiment_id:
                raise ValueError("No active experiment. Please start from the UniProt search.")

            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    "SELECT wt_protein_sequence FROM experiments WHERE experiment_id = %s",
                    (experiment_id,),
                )
                row = cur.fetchone()
            if not row:
                raise ValueError("Experiment not found in database.")
            aminoacid_sequence = row["wt_protein_sequence"]

            if not fasta_file or fasta_file.filename == "":
                raise ValueError("No FASTA file selected.")
            if not allowed_file(fasta_file.filename, FASTA_EXTENSIONS):
                raise ValueError("File type not allowed. Please upload a .fasta, .fa, or .fna file.")

            ext = fasta_file.filename.rsplit(".", 1)[1].lower()
            safe_name = f"{uuid.uuid4()}.{ext}"
            fasta_path = PLASMID_UPLOAD_DIR / safe_name
            fasta_file.save(fasta_path)

            plasmid_sequence = parse_fasta(fasta_path)
            is_valid = validate_protein(plasmid_sequence, aminoacid_sequence)

            if is_valid:
                # Persist the validated plasmid sequence back to the experiment row
                with db.cursor() as cur:
                    cur.execute(
                        "UPDATE experiments SET wt_dna_sequence = %s, plasmid_validated = TRUE WHERE experiment_id = %s",
                        (plasmid_sequence, experiment_id),
                    )
                db.commit()
                session["validated"] = True
                validation_result = {
                    "success": True,
                    "message": "UniProt protein sequence found in plasmid. Validation successful.",
                }
            else:
                validation_result = {
                    "success": False,
                    "message": "The UniProt protein sequence was NOT found in the plasmid.",
                }

        except Exception as e:
            validation_result = {"success": False, "message": f"Error: {e}"}

    return render_template(
        "staging/plasmid_upload.html",
        validation_result=validation_result,
        uniprot_id=uniprot_id,
    )
