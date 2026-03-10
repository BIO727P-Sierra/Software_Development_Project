# File Formats

The portal accepts two types of file uploads: a FASTA file for the plasmid sequence, and either a JSON or TSV file for variant experiment data.

---

## Plasmid FASTA

Used in [Step 2: Plasmid Upload](../pipeline/plasmid-upload.md).

### Accepted extensions

`.fasta`, `.fa`, `.fna`

### Format requirements

- Must begin with a `>` header line (content of the header is ignored)
- Sequence lines follow the header
- Nucleotides must be `A`, `C`, `G`, `T`, or `N` (upper or lowercase — normalised to uppercase)
- Whitespace and blank lines are stripped automatically

### Example

```text title="wildtype_plasmid.fasta"
>pUC19_EGFR_insert
ATGCGTAAAGCGTTTCAGCAGATCCTGGAGCAGAAGCTGATCAGCGAGGAAGATCTGAA
TTTCAACGACATCGTGACCACAGTGCAGCAGATCGACATCGCCTACGGCATCGTGCTGG
AGCAGTTCAACCTGCTGGAGCAGTTCAACCCCCTGGAGCAGTTCAATGAGCTGCAGCAG
...
```

---

## Experiment Data

=== "JSON"

    Used in [Step 3: Experiment Data Upload](../pipeline/experiment-upload.md).

    **Format requirements**

    - Must be a **JSON array** of objects (not a single object or nested structure)
    - Each object represents one plasmid variant

    **Required fields**

    | Field | Type | Description |
    |---|---|---|
    | `Assembled_DNA_Sequence` | string | Full assembled plasmid DNA sequence |
    | `Directed_Evolution_Generation` | integer | Generation number in the evolution campaign |
    | `DNA_Quantification_fg` | number | DNA yield in femtograms |
    | `Plasmid_Variant_Index` | integer | Unique identifier for this variant within the experiment |

    **Optional fields**

    | Field | Type | Description |
    |---|---|---|
    | `Protein_Sequence` | string | Translated protein sequence (if available) |
    | `Protein_Quantification_pg` | number | Protein yield in picograms |
    | `Parent_Plasmid_Variant` | integer | `Plasmid_Variant_Index` of the parent variant |
    | `Control` | any | Marks this variant as a control (stored in metadata) |

    Any additional fields are stored in the `variants.metadata` JSONB column.

    **Example**

    ```json title="experiment_gen1.json" linenums="1"
    [
      {
        "Plasmid_Variant_Index": 1,
        "Directed_Evolution_Generation": 1,
        "Assembled_DNA_Sequence": "ATGCGTAAAGCGTTTCAG...",
        "DNA_Quantification_fg": 245.6,
        "Protein_Sequence": "MRKAFQ...",
        "Protein_Quantification_pg": 18.3,
        "Parent_Plasmid_Variant": null
      },
      {
        "Plasmid_Variant_Index": 2,
        "Directed_Evolution_Generation": 1,
        "Assembled_DNA_Sequence": "ATGCGTAAAGCATTTCAG...",
        "DNA_Quantification_fg": 310.2,
        "Protein_Quantification_pg": 22.1,
        "Parent_Plasmid_Variant": null
      }
    ]
    ```

=== "TSV"

    Used in [Step 3: Experiment Data Upload](../pipeline/experiment-upload.md).

    **Format requirements**

    - Tab-delimited with a **header row** as the first line
    - All required column names must be present in the header (order does not matter)
    - Each subsequent row is one variant

    **Required columns**

    Same as JSON — `Assembled_DNA_Sequence`, `Directed_Evolution_Generation`, `DNA_Quantification_fg`, `Plasmid_Variant_Index`.

    **Example**

    ```text title="experiment_gen1.tsv" linenums="1"
    Plasmid_Variant_Index	Directed_Evolution_Generation	Assembled_DNA_Sequence	DNA_Quantification_fg	Protein_Quantification_pg
    1	1	ATGCGTAAAGCGTTTCAG...	245.6	18.3
    2	1	ATGCGTAAAGCATTTCAG...	310.2	22.1
    3	2	ATGCTTAAAGCGTTTCAG...	198.4	15.7
    ```

---

## QC rules

Records are rejected before database insertion if any of these fields are missing or empty:

```python title="qc.py — rejection criteria" linenums="1"
qc_fields = [
    "plasmid_variant_index",
    "assembled_dna_sequence",
    "generation",
    "dna_yield"
]
```

!!! warning "Rejected records"
    Rejected records are shown on the upload results page with a reason. They are **not inserted** into the database — fix the source data and re-upload if needed.
