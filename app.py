import os
import uuid

from flask import Flask, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from pathlib import Path


from parse_data import parse_data
from qc import validate_data
from feedback import build_feedback, error_feedback
from FASTA_parsing_logic import parse_file as parse_fasta

app = Flask(__name__)

# Upload folders

PLASMID_UPLOAD_DIR = Path("uploads/plasmids")
EXPERIMENT_DATA_UPLOAD_DIR = Path("uploads/experiments")

PLASMID_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENT_DATA_UPLOAD_DIR.mkdir(parenrs=True, exist_ok=True)

# File extensions allowed

fasta_ext = {"fasta", "fa", "fna"}
experiment_ext = {"json", "tsv"}

def allowed_file(filename, allowed_set):
    return "." in filename and filename-rsplit(".", 1)[1].lower in allowed_set

@app.route("/", methods=["GET", "POST"])
def upload_file():
    feedback = None

    if request.method == "POST":
        fasta_file = request.files.get("fasta_file")
        experiment_file = request.files.get("experiment_file")

        try:
            # Upload FASTA Files
            if not fasta_file or fasta_file.filename == "":
                raise ValueError("No File detected.")
            
            if not allowed_file(fasta_file.filename, fasta_ext):
                raise ValueError("Invalid file type, please upload FASTA.")
            
            fasta_name = secure_filename(fasta_file.filename)
            fasta_extension = fasta_name.rsplit(".", 1)[1].lower()
            fasta_safe = f"{uuid.uuid4()}.{fasta_extension}"

            fasta_path = PLASMID_UPLOAD_DIR / fasta_safe
            fasta_file.save(fasta_path)

            fasta_sequence = parse_fasta(fasta_path)

            # Upload Experiment Files

            if not experiment_file or experiment_file.filename == "":
                raise ValueError("No File detected.")
            
            if not allowed_file(experiment_file.filename, experiment_ext):
                raise ValueError("Invalid file type, please upload FASTA.")
            
            experiment_name = secure_filename(experiment_file.filename)
            exp_extension = experiment_name.rsplit(".", 1)[1].lower()
            experiment_safe = f"{uuid.uuid4()}.{exp_extension}"

            experiment_path = EXPERIMENT_DATA_UPLOAD_DIR / experiment_safe
            experiment_file.save(experiment_path)

            parsed_records = parse_data(experiment_path)
            valid_records, rejected_records = validate_data(parsed_records)

            feedback = build_feedback(valid_records, rejected_records)
            feedback["sequence_length"] = len(fasta_sequence)

        except Exception as e:
            feedback = error_feedback(e)
    
    return render_template("upload.html", feedback=feedback)

if __name__ == "__main__":
    app.run(debug=True)
