# 🧬 Directed Evolution Portal

A web application for tracking and analysing protein directed evolution experiments — from plasmid upload through automated ORF analysis and variant scoring.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## What it does

The portal guides researchers through a four-step workflow:

1. **UniProt Search** — fetch a wild-type reference protein by accession ID
2. **Plasmid Upload** — validate that the WT protein is encoded in your plasmid FASTA
3. **Experiment Data Upload** — upload variant sequencing data (JSON or TSV)
4. **ORF Analysis** — automatically identify and score the coding sequence in every variant

Results are stored in PostgreSQL and displayed in a results table per experiment.

---

## Quick start

**Requirements:** [Docker Desktop](https://docs.docker.com/get-docker/) (no local PostgreSQL needed)

```bash
git clone https://github.com/BIO727P-Sierra/Software_Development_Project.git
cd Software_Development_Project
docker compose up --build
```

The app will be available at **http://localhost:8080** once both containers are healthy.


---

## Accessing the database

To inspect the database using a GUI such as [PgAdmin](https://www.pgadmin.org/):

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `direct_evolution` |
| Username | `sierra` |
| Password | `sierra` |

---

## Common commands

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
docker compose logs app     # Flask / Gunicorn
docker compose logs db      # PostgreSQL
docker compose logs -f app  # follow live
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| Authentication | Flask-Login |
| Database | PostgreSQL 16 |
| DB driver | psycopg3 |
| Sequence analysis | Biopython |
| Deployment | Docker Compose + Gunicorn |

---

## Project structure

```
.
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # Flask app image
├── schema.sql                    # Database schema (auto-applied on first run)
├── requirements.txt              # Python dependencies
├── wsgi.py                       # Gunicorn entry point
├── __init__.py                   # Flask app factory
├── auth.py                       # User registration & login
├── home.py                       # Dashboard & index
├── uniprot.py / uniprotAPI.py    # UniProt integration
├── FASTA_upload.py               # Plasmid upload & validation
├── FASTA_parsing_logic.py        # FASTA parsing utilities
├── experiment_upload.py          # Variant data upload (JSON/TSV)
├── parse_data.py / qc.py         # Parsing & QC
├── feedback.py                   # Upload feedback formatting
├── sequence_processor.py         # ORF discovery, scoring & selection engine
├── analysis.py                   # Analysis routes & DB write-back
├── db.py                         # Database connection management
└── uploads/                      # Persisted uploaded files (Docker volume)
```

---

## Documentation

Full documentation: **https://your-org.github.io/directed-evolution-portal**

| Section | Description |
|---|---|
| [Getting Started](https://your-org.github.io/directed-evolution-portal/getting-started/) | Docker setup, database access, logs |
| [Pipeline Overview](https://your-org.github.io/directed-evolution-portal/pipeline/overview/) | Full experiment workflow |
| [ORF Analysis](https://your-org.github.io/directed-evolution-portal/pipeline/orf-analysis/) | Sequence processing engine deep dive |
| [Database Schema](https://your-org.github.io/directed-evolution-portal/reference/database-schema/) | All tables and columns |
| [File Formats](https://your-org.github.io/directed-evolution-portal/reference/file-formats/) | FASTA, JSON, TSV specs and examples |

---

## Deploying the docs

```bash
pip install mkdocs mkdocs-material
mkdocs serve        # preview at http://127.0.0.1:8000
mkdocs gh-deploy    # publish to GitHub Pages
```

---

## License

MIT
