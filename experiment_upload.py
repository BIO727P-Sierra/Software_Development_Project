import uuid

from flask import Blueprint, render_template, request, redirect, flash, url_for, session 
from werkzeug.utils import secure_filename
from pathlib import Path 

# Import python scripts
from app.parse_data import parse_data
from app.qc import validate_data
from app.feedback import build_feedback, error_feedback
from app.FASTA_parsing_logic import parse_file as parse_file

bp = Blueprint("experiment_upload", __name__, url_prefix="/experiment_upload")

# Upload directories for storage
EXPERIMENT_DATA_UPLOAD_DIR = Path("uploads/experiments")
EXPERIMENT_DATA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
experiment_ext = {"json", "tsv"}

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# Upload page
@bp.route("/", methods=["GET", "POST"])
def experiment_upload():
    # Creating sessions so that the page can be refreshed
    experiment_feedback = None

    if not session.get("validated"):
        return redirect(url_for("FASTA_upload.plasmid_upload"))

    if request.method == "POST":

        experiment_file = request.files.get("experiment_file")
        
        try:
            # Upload JSON or TSV
            if not experiment_file or experiment_file.filename == "":
                raise ValueError("No file detected.")
            
            parsed_data = parse_data(experiment_file)
            valid_records, rejected_records = validate_data(parsed_data)

            experiment_feedback = build_feedback(valid_records, rejected_records)

            # Storing the parsed valid data in session
            session["valid_records"] = valid_records

        except Exception as e:
            experiment_feedback = error_feedback(e)

    return render_template(
        "staging/experiment_upload.html", 
        experiment_feedback = experiment_feedback
    )

@bp.route("/staging")
def experiment_staging():
    if not session.get("validated"):
        return redirect(url_for("FASTA_upload.plasmid_upload"))
    return render_template("staging/experiment_upload.html")
