# Local Setup Guide for Stage + ORF

## Structure

```
project/
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── home.py
│   ├── dev.py                  ← temporary testing file, delete when auth is built
│   ├── analysis.py
│   ├── experiment_upload.py
│   ├── FASTA_upload.py
│   ├── FASTA_parsing_logic.py
│   ├── feedback.py
│   ├── parse_data.py
│   ├── qc.py
│   ├── sequence_processor.py
│   └── templates/
│       ├── home/
│       │   └── index.html
│       ├── staging/
│       │   ├── plasmid_upload.html
│       │   └── experiment_upload.html
│       └── analysis/
│           └── results.html
├── schema.sql
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
```

---

## Issues & Fixes Applied

The following bugs were identified and fixed.

**1. Typo in `plasmid_upload.html`**
`{{ validation_resultmessage }}` was missing a dot. Fixed to `{{ validation_result.message }}`.

**2. Home page auth links caused a crash**
The home page referenced `auth.register` and `auth.login` blueprints that don't exist yet. These were removed from `index.html` for now.

**3. `experiment_id` not passed to template**
In `experiment_upload.py`, `experiment_id` was read from the session into a local variable but never passed to the template. Fixed by adding it to the `render_template` call:
```python
return render_template(
    "staging/experiment_upload.html",
    experiment_feedback=experiment_feedback,
    experiment_id=experiment_id,  # ← added
)
```

**5. `FASTA_upload.py` reading `wt_protein_sequence` from session instead of DB**
Originally the code read `aminoacid_sequence = session.get("aminoacid_sequence")` which was a placeholder for the UniProt step. Fixed to read directly from the database:
```python
db = get_db()
with db.cursor() as cur:
    cur.execute(
        "SELECT wt_protein_sequence FROM experiments WHERE experiment_id = %s",
        (session.get("experiment_id"),)
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Experiment not found in database.")
    aminoacid_sequence = row["wt_protein_sequence"]
```

**6. `generation` field not cast to int in `parse_data.py`**
The schema defines `generation INTEGER NOT NULL` but it was being stored as a raw string. Fixed:
```python
# Before:
"generation": row.get("Directed_Evolution_Generation"),

# After:
"generation": int(row["Directed_Evolution_Generation"]),
```


## Missing Pieces

The following upstream steps are not yet implemented. The manual SQL insertions below exist to bypass them for testing purposes only.

- **UniProt lookup** — fetches `wt_protein_sequence` and `uniprot_id` from UniProt API and stores them in the DB
- **Auth system** — user registration and login (`auth` blueprint)
- **Experiment creation route** — creates the experiment row in the DB and writes `experiment_id` to the session

---

## Step 1 — Prerequisites

Make sure you have the following installed:
- Docker Desktop
- Python 3.12+
- pip

---

## Step 2 — Install dependencies

From your project root:

```bash
pip install -r requirements.txt
```

---

## Step 3 — Start the database

```bash
docker compose up -d
```

Verify it is running:

```bash
docker compose ps
```

You should see `direct_evolution_db` with status `running`.

---

## Step 4 — Manually insert test data

Since the UniProt lookup and auth steps are not built yet, insert the minimum required data directly into the database.

Connect to psql:

```bash
docker exec -it direct_evolution_db psql -U sierra -d direct_evolution
```

Insert a test user:

```sql
INSERT INTO users (email, password_hash)
VALUES ('test@test.com', 'placeholder')
RETURNING id;
```

Note the `id` returned — use it in the next command (should be `1` on a fresh database).

Insert the experiment with the WT protein sequence from UniProt (O34996):

```sql
INSERT INTO experiments (
    user_id,
    experiment_name,
    uniprot_id,
    wt_protein_sequence,
    wt_dna_sequence,
    plasmid_validated
)
VALUES (
    1,
    'BSU DNA Pol I Directed Evolution Batch 1',
    'O34996',
    'MTERKKLVLVDGNSLAYRAFFALPLLSNDKGVHTNAVYGFAMILMKMLEDEKPTHMLVAFDAGKTTFRHGTFKEYKGGRQKTPPELSEQMPFIRELLDAYQISRYELEQYEADDIIGTLAKSAEKDGFEVKVFSGDKDLTQLATDKTTVAITRKGITDVEFYTPEHVKEKYGLTPEQIIDMKGLMGDSSDNIPGVPGVGEKTAIKLLKQFDSVEKLLESIDEVSGKKLKEKLEEFKDQALMSKELATIMTDAPIEVSVSGLEYQGFNREQVIAIFKDLGFNTLLERLGEDSAEAEQDQSLEDINVKTVTDVTSDILVSPSAFVVEQIGDNYHEEPILGFSIVNETGAYFIPKDIAVESEVFKEWVENDEQKKWVFDSKRAVVALRWQGIELKGAEFDTLLAAYIINPGNSYDDVASVAKDYGLHIVSSDESVYGKGAKRAVPSEDVLSEHLGRKALAIQSLREKLVQELENNDQLELFEELEMPLALILGEMESTGVKVDVDRLKRMGEELGAKLKEYEEKIHEIAGEPFNINSPKQLGVILFEKIGLPVVKKTKTGYSTSADVLEKLADKHDIVDYILQYRQIGKLQSTYIEGLLKVTRPDSHKVHTRFNQALTQTGRLSSTDPNLQNIPIRLEEGRKIRQAFVPSEKDWLIFAADYSQIELRVLAHISKDENLIEAFTNDMDIHTKTAMDVFHVAKDEVTSAMRRQAKAVNFGIVYGISDYGLSQNLGITRKEAGAFIDRYLESFQGVKAYMEDSVQEAKQKGYVTTLMHRRRYIPELTSRNFNIRSFAERTAMNTPIQGSAADIIKKAMIDMAAKLKEKQLKARLLLQVHDELIFEAPKEEIEILEKLVPEVMEHALALDVPLKVDFASGPSWYDAK',
    '',
    false
)
RETURNING experiment_id;
```

Note: `wt_dna_sequence` is empty here — it will be populated when the FASTA file is uploaded through the app.

Verify:

```sql
SELECT experiment_id, experiment_name, uniprot_id, length(wt_protein_sequence) FROM experiments;
```

Exit psql:

```bash
\q
```

---

## Step 5 — Start Flask

Open a new terminal and run:

```bash
export DATABASE_URL=postgresql://sierra:sierra@localhost:5432/direct_evolution
export FLASK_APP=app
export SECRET_KEY=dev-secret
flask run
```

Keep this terminal open. Visit `http://127.0.0.1:5000` — you should see the home page.

---

## Step 6 — Set the session

Since the auth and experiment creation steps are not built yet, use the temporary dev route to set the session manually.

Visit:

```
http://127.0.0.1:5000/dev/set-session/1
```

You should see: `Session set: experiment_id=1`

---

## Step 7 — Test the FASTA upload

Go to:

```
http://127.0.0.1:5000/plasmid_upload/
```

Upload `pET-28a_BSU_DNA_Pol_I_WT.fa`. You should see:

```
Validation Successful
Uniprot data aligns with plasmid sequence.
```

Click **Proceed to Experiment Data Upload**.

---

## Step 8 — Test the experiment data upload

Upload `DE_BSU_Pol_Batch_1.json`. You should see:

```
Experiment Data Upload Successful
Rows Parsed: 301
Rows Rejected: 0
```

Click **Run Step 1 Analysis**.

---

## Step 9 — View results

You will be redirected to:

```
http://127.0.0.1:5000/analysis/results/experiment/1
```

This shows the Step 1 ORF identification results for all 301 variants.

---

## Resetting the database

To wipe all data and start fresh:

```bash
docker compose down -v
docker compose up -d
```

Then repeat from Step 4.

---

## Notes for future development

- Delete `app/dev.py` and remove it from `__init__.py` once the auth system is built
- `variants.protein_sequence` is `NOT NULL` in the schema but is not present in the JSON file — currently inserted as an empty string placeholder; should be populated during Step 1 or made nullable
- `Protein_Quantification_pg` in the JSON file does not match `Protein_Quantification_fg` expected by `parse_data.py` — column name needs aligning

