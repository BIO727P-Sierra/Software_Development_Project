# Getting Started

This guide walks you through running the Directed Evolution Portal locally using Docker Compose. No local PostgreSQL installation is required — the database runs entirely inside Docker.

---

## Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) installed (includes Docker Compose)
- Git

---

## 1. Clone the repository

```bash title="Terminal"
git clone https://github.com/your-org/directed-evolution-portal.git
cd directed-evolution-portal
```

---

## 2. Configure environment variables

The app is configured via environment variables defined in `docker-compose.yml`. For local development the defaults work out of the box, but **change these before any production deployment**:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgres://sierra:sierra@db:5432/direct_evolution` | PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production` | Flask session signing key — **must be changed in production** |
| `POSTGRES_DB` | `direct_evolution` | Database name |
| `POSTGRES_USER` | `sierra` | Database user |
| `POSTGRES_PASSWORD` | `sierra` | Database password |

To override values without editing the compose file, create a `.env` file in the project root:

```bash title=".env"
SECRET_KEY=your-long-random-secret-key
POSTGRES_PASSWORD=your-secure-password
```

!!! warning "Production deployments"
    Never use the default `SECRET_KEY` or database credentials in production. Generate a strong secret key with:
    ```bash title="Terminal"
    python -c "import secrets; print(secrets.token_hex(32))"
    ```

---

## 3. Start the application

```bash title="Terminal"
docker compose up --build
```

Docker Compose will:

1. Pull the PostgreSQL 16 image and start the database
2. Run `schema.sql` to initialise all tables on first startup
3. Build the Flask app image and start Gunicorn on port `5000` (mapped to `8080` on your host)

The app will be available at **[http://localhost:8080](http://localhost:8080)** once both containers are healthy.

!!! note "First startup"
    The app container waits for the database healthcheck to pass before starting. This typically takes 10–20 seconds on first run.

!!! note "Port 8080 — why not 5000?"
    macOS reserves port 5000 for AirPlay Receiver by default. The container still listens on `5000` internally; only the host-side binding is changed to `8080`.

---

## 4. Register an account

Navigate to [http://localhost:8080](http://localhost:8080) and click **Register** to create your first user account. All experiment data is scoped to the logged-in user.

---

## 5. Run in the background

```bash title="Terminal"
docker compose up -d
```

To stop (keeps the database volume intact):

```bash title="Terminal"
docker compose down
```

To stop and remove all data including the database volume:

```bash title="Terminal"
docker compose down -v
```

---

## 6. Accessing the database directly

### Via PgAdmin (GUI)

If you want to inspect the database using a GUI client such as [PgAdmin](https://www.pgadmin.org/), use these connection settings:

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `direct_evolution` |
| Username | `sierra` |
| Password | `sierra` |

### Via connection string

If connecting from a local Flask instance or other tool outside Docker:

```bash title="Connection string"
postgresql://sierra:sierra@localhost:5432/direct_evolution
```

---

## 7. Resetting the database

The database is stored in a Docker volume and persists between container restarts. If you change `schema.sql` or need a clean slate, you must destroy the volume and rebuild:

```bash title="Terminal"
docker compose down -v
docker compose up --build
```

!!! warning
    `docker compose down -v` permanently deletes all data in the database. Make sure you have exported anything you need before running this.

---

## 8. Viewing logs

```bash title="Terminal"
docker compose logs app   # Flask / Gunicorn logs
docker compose logs db    # PostgreSQL logs
```

Add `-f` to follow logs in real time:

```bash title="Terminal"
docker compose logs -f app
```

---

## Project structure

```
.
├── docker-compose.yml       # Container orchestration
├── Dockerfile               # Flask app image build
├── schema.sql               # Database schema (auto-applied on first run)
├── requirements.txt         # Python dependencies
├── wsgi.py                  # Gunicorn entry point
├── __init__.py              # Flask app factory
├── auth.py                  # User registration & login
├── home.py                  # Dashboard & index routes
├── uniprot.py               # UniProt search & confirmation
├── uniprotAPI.py            # UniProt REST API client
├── FASTA_upload.py          # Plasmid FASTA upload & validation
├── FASTA_parsing_logic.py   # FASTA parsing utilities
├── experiment_upload.py     # Variant data upload (JSON/TSV)
├── parse_data.py            # File parsing & normalisation
├── qc.py                    # QC validation rules
├── feedback.py              # Upload feedback formatting
├── sequence_processor.py    # ORF discovery, scoring & selection engine
├── analysis.py              # Analysis routes & DB write-back
├── db.py                    # Database connection management
└── uploads/                 # Persisted uploaded files (Docker volume)
```

---

## Installing Python dependencies locally (optional)

If you want to run or test outside Docker:

```bash title="Terminal"
pip install -r requirements.txt
```

Then set the `DATABASE_URL` environment variable pointing to a running PostgreSQL instance and run:

```bash title="Terminal"
python wsgi.py
```
