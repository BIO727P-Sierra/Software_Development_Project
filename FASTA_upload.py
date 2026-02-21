import uuid

from flask import Blueprint, render_template, request, redirect, flash, url_for, session 
from werkzeug.utils import secure_filename
from pathlib import Path 

# Import python scripts
from app.parse_data import parse_data
from app.qc import validate_data
from app.feedback import build_feedback, error_feedback
from app.FASTA_parsing_logic import parse_file as parse_fasta
from app.FASTA_parsing_logic import validate_protein

bp = Blueprint("FASTA_upload", __name__, url_prefix="/plasmid_upload")

# Upload directories for storage
PLASMID_UPLOAD_DIR = Path("uploads/plasmids")
PLASMID_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
fasta_ext = {"fasta", "fa", "fna"}

def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# FASTA upload page
@bp.route("/", methods=["GET", "POST"])
def plasmid_upload():
    # Creating sessions so that the page can be refreshed
    validation_result = None

    if request.method == "POST":

        fasta_file = request.files.get("fasta_file")
        aminoacid_sequence = session.get("aminoacid_sequence")

        # -------------------------
        # If testing without UniProt data, change aminoacid_sequence to a string of amino acids that matches the file you upload
        # E.g if using the example  data FASTA, change this variable to "WRMGRAL*RR" as these are the translated bases
        # -------------------------

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
            plasmid_sequence = parse_fasta(fasta_path)

            is_valid = validate_protein(plasmid_sequence, aminoacid_sequence)

            if is_valid:
                validation_result = {
                    "success": True,
                    "message": "Uniprot data aligns with plasmid sequence. Validation successful."
                }
                session["validated"] = True
            else:
                validation_result = {
                    "success": False,
                    "message": "The protein sequence provided by UniProt was NOT found in the plasmid."
                }

        except Exception as e:
            validation_result = {
                "success": False,
                "message": f"FASTA file Error: {str(e)}"
            }

    return render_template(
        "staging/plasmid_upload.html", 
        validation_result = validation_result
    )

@bp.route("/staging")
def experiment_upload():
    if not session.get("validated"):
        return redirect(url_for("FASTA_upload.plasmid_upload"))
    return render_template("experiment_upload.html")


