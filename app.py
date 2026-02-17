import os
import uuid

from flask import Flask, render_template, request, redirect, flash, url_for, session 
from werkzeug.utils import secure_filename
from pathlib import Path 

# Import python scripts
from parse_data import parse_data
from qc import validate_data
from feedback import build_feedback, error_feedback
from FASTA_parsing_logic import parse_file as parse_fasta

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev_secret_key")

# Upload direc  tories for storage
PLASMID_UPLOAD_DIR = Path("uploads/plasmids")
EXPERIMENT_DATA_UPLOAD_DIR = Path("uploads/experiments")

PLASMID_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DATA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
fasta_ext = {"fasta", "fa", "fna"}
experiment_ext = {"json", "tsv"}

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# Upload page
@app.route("/", methods=["GET", "POST"])

def upload_file():
    # Creating sessions so that the page can be refreshed
    fasta_feedback = None
    experiment_feedback = None

    if request.method == "POST":

        fasta_file = request.files.get("fasta_file")
        experiment_file = request.files.get("experiment_file")

        try:
            # Upload FASTA
            if not fasta_file or fasta_file.filename == "":
                raise ValueError("No FASTA file detected.")
            
            if not allowed_file(fasta_file.filename, fasta_ext):
                raise ValueError("File type not allowed, please upload a FASTA file")
            
            fasta_name = secure_filename(fasta_file.filename)
            fasta_extension = fasta_name.rsplit(".", 1)[1].lower()
            safe_fasta = f"{uuid.uuid4()}.{fasta_extension}"

            fasta_path = PLASMID_UPLOAD_DIR / safe_fasta
            fasta_file.save(fasta_path)

            # Using FASTA_parsing_logic.py function to validate FASTA
            fasta_sequence = parse_fasta(fasta_path)

            fasta_feedback = {
                "success": True,
                "message": "Plasmid sequence FASTA parsed successfully",
                "sequence_length": len(fasta_sequence)
            }

            session["fasta_sequence"] = fasta_sequence

        except Exception as e:
            fasta_feedback = {
                "success": False,
                "message": f"FASTA file Error: {str(e)}"
            }
        
        try:
            # Upload JSON or TSV
            if not experiment_file or experiment_file.filename == "":
                raise ValueError("No file detected.")
            
            if not allowed_file(experiment_file.filename, experiment_ext):
                raise ValueError("Unsupported file type. Please upload .json or .tsv")
            
            experiment_name = secure_filename(experiment_file.filename)
            experiment_extension = experiment_name.rsplit(".", 1)[1].lower()
            safe_experiment_file = f"{uuid.uuid4()}.{experiment_extension}"

            experiment_path = EXPERIMENT_DATA_UPLOAD_DIR / safe_experiment_file
            experiment_file.save(experiment_path)

            # Parse and QC experiment records

            parsed_records = parse_data(experiment_path)
            valid_records, rejected_records = validate_data(parsed_records)

            experiment_feedback = build_feedback(valid_records, rejected_records)

            # Storing the parsed valid data in session
            session["valid_records"] = valid_records

        except Exception as e:
            experiment_feedback = error_feedback(e)
        return render_template(
            "upload.html", 
            fasta_feedback = fasta_feedback,
            experiment_feedback = experiment_feedback
        )


    return render_template(
        "upload.html", 
        fasta_feedback = fasta_feedback,
        experiment_feedback = experiment_feedback
    )

if __name__ == "__main__":
    app.run(debug=True)
