# Step 1: UniProt Search

## What this step does

The experiment begins by fetching the **wild-type (WT) reference protein** from the UniProt database. This protein sequence becomes the anchor for every downstream step — plasmid validation checks the protein is encoded in the plasmid, and ORF analysis scores variant sequences against it.

---

## For scientists

1. Navigate to **New Experiment** from the dashboard
2. Enter a valid UniProt accession ID (e.g. `P00533` for human EGFR)
3. Review the retrieved protein sequence and feature table
4. Click **Confirm & Store Data** to create the experiment and proceed

The feature table shows annotated regions from UniProt — active sites, binding sites, domains, signal peptides, transmembrane regions, and secondary structure elements. These are stored alongside the experiment for future reference.

!!! tip "Finding your UniProt ID"
    Search for your protein at [uniprot.org](https://www.uniprot.org). The accession ID is the alphanumeric code in the URL and entry header (e.g. `P00533`, `Q9Y2T1`).

---

## For developers

### Route

| Method | URL | Handler |
|---|---|---|
| GET / POST | `/uniprot/` | `uniprot.uniprot_search` |
| GET | `/uniprot/confirmation` | `uniprot.confirmation` |
| GET | `/uniprot/store` | `uniprot.data_stored` |

### What gets fetched from UniProt

The `uniprotAPI.py` module makes three requests to the UniProt REST API:

```
GET https://rest.uniprot.org/uniprotkb/{id}.txt        ← validates the ID exists
GET https://rest.uniprot.org/uniprotkb/{id}.fasta      ← retrieves protein sequence
GET https://rest.uniprot.org/uniprotkb/{id}.json?fields=... ← retrieves feature annotations
```

The feature fields fetched cover: variants, active sites, binding sites, PTMs, domains, motifs, secondary structure, and more. See `uniprotAPI.py` for the full field list.

### What gets stored in the database

On confirmation, an `experiments` row is created:

```sql
INSERT INTO experiments
    (user_id, experiment_name, uniprot_id, wt_protein_sequence,
     wt_dna_sequence, uniprot_features)
VALUES (...)
```

| Column | Value at this stage |
|---|---|
| `uniprot_id` | The submitted accession ID |
| `wt_protein_sequence` | Full protein sequence from UniProt FASTA |
| `wt_dna_sequence` | Empty string — filled at plasmid upload |
| `uniprot_features` | JSONB array of `{feature_type, start_location, end_location}` |

### Session state set

```python
session["uniprot_id"] = uniprot_id
session["experiment_id"] = experiment_id
session["validated"] = False   # plasmid not yet validated
```

### Error handling

| Condition | Behaviour |
|---|---|
| Invalid UniProt ID | Flash message shown, form re-rendered |
| UniProt API unreachable | Returns error string from `uniprotAPI.py` |
| Session expired on `/store` | Redirects to UniProt search with flash |
