# Directed Evolution Portal

A web application for tracking and analysing protein directed evolution experiments -- from plasmid upload through automated ORF analysis, mutation detection, activity scoring, and visualisation.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## What it does

The portal guides researchers through a multi-step workflow:

1. **UniProt Search** — fetch a wild-type reference protein by accession ID, including domain/feature annotations  
2. **Plasmid Upload** — upload and validate that the WT protein is encoded in your plasmid FASTA  
3. **Experiment Data Upload** — upload variant sequencing data (JSON or TSV) with DNA/protein quantification  
4. **ORF Analysis** — automatically identify and score the target coding sequence in every variant  
5. **Mutation Detection** — pairwise alignment against the WT to classify mutations (missense, nonsense, insertions, deletions)  
6. **Activity Scoring** — log2-based activity scores from DNA/protein fold-change vs WT  
7. **Visualisation** — mutation fingerprints, activity landscapes (3D/2D PCA), and generation boxplots  
8. **Top Performers** — ranked table of highest-scoring variants  
9. **PDF Reports** — downloadable experiment summaries  
10. **Experiment Management** — save, rename, and delete experiments  

---

## Quick Start

### Requirements
- [Docker Desktop](https://docs.docker.com/get-docker/)

_No local Python or PostgreSQL installation required._

### Run the app

```bash
git clone https://github.com/BIO727P-Sierra/Software_Development_Project.git
cd Software_Development_Project
docker compose up --build
```

The app will be available at:  
http://localhost:8080

---

## Database Access (Optional)

To inspect the database using tools like **PgAdmin**:

| Setting   | Value              |
|----------|-------------------|
| Host     | localhost         |
| Port     | 5432              |
| Database | direct_evolution  |
| Username | sierra            |
| Password | sierra            |

---

## Common Commands

```bash
# Start (foreground)
docker compose up --build

# Start (background)
docker compose up -d

# Stop (keep data)
docker compose down

# Stop and wipe all data
docker compose down -v

# View logs
docker compose logs app
docker compose logs db
docker compose logs -f app
```

---

## Application Flow

```
Register / Login
       |
       v
Search UniProt ID (/uniprot/)
       |
       v
Review protein info + domain features
       |
       v
Store (experiment created)
       |
       v
Upload plasmid FASTA (/plasmid_upload/)
       |
       v
Upload experiment data (/experiment_upload/)
       |
       v
Run ORF Analysis
       |
       v
Results Dashboard
  |        |         |         |
  v        v         v         v
Mutation  Activity  Generation  Top
Plots     Landscape Boxplot     Performers
       |
       v
   PDF Report
```

---

## Tech Stack

| Layer              | Technology |
|-------------------|-----------|
| Web Framework     | Flask 3.1.3 |
| Authentication    | Flask-Login |
| Sessions          | Flask-Session |
| Forms             | Flask-WTF |
| Database          | PostgreSQL 16 |
| DB Driver         | psycopg 3 |
| Sequence Analysis | Biopython |
| Visualisation     | Plotly, Matplotlib |
| Dimensionality    | scikit-learn (PCA) |
| Data Processing   | NumPy, SciPy, Pandas |
| PDF Generation    | ReportLab |
| Deployment        | Docker + Gunicorn |

---

## Database Schema

Managed via `schema.sql` (auto-applied on first run):

| Table         | Purpose |
|--------------|--------|
| users        | Authentication (email, password hash) |
| experiments  | Experiment metadata (WT, UniProt ID, features) |
| variants     | Variant-level results (ORF, activity score) |
| measurements | DNA/protein quantification |
| mutations    | Individual mutation records |

---

## Project Structure

```
.
├── docker-compose.yml
├── Dockerfile
├── schema.sql
├── requirements.txt
├── wsgi.py
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── auth.py
│   ├── home.py
│   ├── uniprot.py
│   ├── uniprotAPI.py
│   ├── FASTA_upload.py
│   ├── FASTA_parsing_logic.py
│   ├── experiment_upload.py
│   ├── parse_data.py
│   ├── qc.py
│   ├── feedback.py
│   ├── sequence_processor.py
│   ├── mutation_calc.py
│   ├── mutation_repository.py
│   ├── activity_score.py
│   ├── analysis.py
│   ├── Mutation_Fingerprinting_Vis.py
│   ├── activity_landscape_vis.py
│   ├── generation_plot.py
│   ├── top_performer_table.py
│   ├── past_experiments.py
│   ├── report.py
│   └── templates/
│
├── uploads/
│   ├── plasmids/
│   └── experiments/
│
└── Example_Data/
```

---

## File Format Reference

### Plasmid FASTA

```fasta
>pET-28a_GFP_WT
TGGCGAATGGGACGCGCCCTGTAGCGGCGCATTAAGCGCGGCGGGTGTG...
```

---

### Experiment Data (TSV / JSON)

| Column                         | Type   | Description |
|--------------------------------|--------|------------|
| Plasmid_Variant_Index          | int    | Variant ID (0 = WT) |
| Parent_Plasmid_Variant         | int    | Parent variant (-1 = WT) |
| Directed_Evolution_Generation  | int    | Generation number |
| Assembled_DNA_Sequence         | string | Full plasmid sequence |
| DNA_Quantification_fg          | float  | DNA yield |
| Protein_Quantification_pg      | float  | Protein yield |
| Control                        | bool   | TRUE = WT |

---

## License

MIT
