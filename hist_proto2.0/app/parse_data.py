import os
import csv
import json

essential_fields = [
    "Assembled_DNA_Sequence",
    "Directed_Evolution_Generation",
    "DNA_Quantification_fg",
    "Plasmid_Variant_Index"
]

optional = [
    "Protein_Sequence",
    "Protein_Quantification_pg",  # fixed from fg to pg
    "Control",
    "Parent_Plasmid_Variant",
]


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}

# Load the file based on extension
def load_file(file_path):
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")
    
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".json":
        return load_jsonfile(file_path)
    
    elif extension == ".tsv":
        return load_tsvfile(file_path)
    
    else:
        raise ValueError("Unsupported file type. Please upload .json or .tsv")
    
# Load the JSON file
def load_jsonfile(file_path):

    try:
        with open(file_path, "r") as file:
            data = json.load(file)

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON file is invalid: {e}")
    
    if not isinstance(data, list):
        raise ValueError(f"JSON file must contain records.")

    # Attaching row numbers to JSON to help pinpoint what row is being rejected
    return [
        {"__row_number__": i + 1, **row}
        for i, row in enumerate(data)
    ]

# Load the TSV file
def load_tsvfile(file_path):
    
    tsv_records = []

    try:
        with open(file_path, "r", newline='') as file:
            tsv_reader = csv.DictReader(file, delimiter='\t')

            if tsv_reader.fieldnames is None:
                raise ValueError("The TSV file is missing a header row")
            
            missing_columns = [f for f in essential_fields if f not in tsv_reader.fieldnames]

            if missing_columns:
                raise ValueError(f"TSV is missing required columns: {missing_columns}")
            
            # Numbering TSV starting at 2 as row 1 is the header
            for row_number, row in enumerate(tsv_reader, start=2):
                row["__row_number__"] = row_number
                tsv_records.append(row)

    except csv.Error as e:
            raise ValueError(f"The TSV file is invalid: {e}")
    
    return tsv_records

def normalised_data(records):

    normalised = []

    for row in records:
        
        parsed_data = {
            "row_number": row.get("__row_number__"),
            "plasmid_variant_index": row.get("Plasmid_Variant_Index"),
            "protein_sequence": row.get("Protein_Sequence"),
            "assembled_dna_sequence": row.get("Assembled_DNA_Sequence"),
            "parent_variant_id": row.get("Parent_Plasmid_Variant"),
            "generation": int(row["Directed_Evolution_Generation"]) if row.get("Directed_Evolution_Generation") is not None else None,  # cast to int and fix error
            "dna_yield": float(row["DNA_Quantification_fg"]) if row.get("DNA_Quantification_fg") else None,
            "protein_yield": float(row["Protein_Quantification_pg"]) if row.get("Protein_Quantification_pg") else None,  # fixed from fg to pg
            "is_control": _as_bool(
                row.get("Control", row.get("control", row.get("is_control")))
            ),
        }
                       
        metadata = {
            k: v for k, v in row.items()
            if k not in essential_fields and k not in optional
        }

        parsed_data["metadata"] = metadata

        normalised.append(parsed_data)

    return normalised

# Main pipeline --------------------------------------------------------------

def parse_data(file_path):
    
    data = load_file(file_path)
    
    return normalised_data(data)


