# Import from libraries
from pathlib import Path  # Imports Path class where path represents file systems
from Bio.Seq import Seq

# Set used to store nucleotides in a variable
valid_nucleotides = {"A", "C", "G", "T", "N"}  # Where "N" represents an unknown or an ambiguous nucleotide

# Creates function for parsing FASTA files and returns output as a single string
# Raises ValueError if the file is invalid
def parse_file(fasta_file: Path) -> str:

    # Open the file object "f" in read "r" mode
    with open(fasta_file, "r") as f:
        lines = [line.strip() for line in f if line.strip()]  # Remove whitespace and newlines

    # Check for an empty file
    if not lines:
        raise ValueError("Empty fasta file")

    # Check that FASTA header is present
    # First non-empty line should start with > in a FASTA file
    if not lines[0].startswith(">"):
        raise ValueError("Missing FASTA header")

    # Build DNA sequence
    # Normalises sequence into uppercase
    plasmid_sequence = "".join(lines[1:]).upper()

    # Where header exists but no sequence is present
    if not plasmid_sequence:
        raise ValueError("No sequence found")

    # Checks that all characters in the sequence are valid nucleotides
    if not set(plasmid_sequence).issubset(valid_nucleotides):
        raise ValueError("Sequence contains invalid nucleotide characters")

    # Returns a validated DNA sequence
    return plasmid_sequence

def validate_protein(plasmid_sequence, aminoacid_sequence):
    circular_seq = plasmid_sequence + plasmid_sequence

    seq_obj = Seq(circular_seq)

    for frame in range(3):
        translated = str(seq_obj[frame:].translate(to_stop=False))
        if aminoacid_sequence in translated:
            return True
        
    reverse_seq = seq_obj.reverse_complement()
    for frame in range(3):
        translated = str(reverse_seq[frame:].translate(to_stop=False))
        if aminoacid_sequence in translated:
            return True
        
    return False