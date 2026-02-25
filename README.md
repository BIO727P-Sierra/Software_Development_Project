# 🧬 Directed Evolution Portal — Changelog

> **Scope:** Bring existing codebase to a fully runnable state. No new features introduced — business logic (ORF analysis, UniProt API, QC pipeline) is unchanged.

---
## Overview

The original codebase contained two partially-merged development branches. Neither branch was runnable on its own. The following problems were present:

- No `Dockerfile` or app service in `docker-compose.yml` - added
- Two different `__init__.py` files registering different subsets of blueprints - merged into one
- A mixed SQLAlchemy/psycopg database layer that caused `RuntimeError` on startup
- `data_stored()` in `uniprot.py` returned a bare string and never wrote to the database, so `experiment_id` was never set in the session
- Absolute imports (`from app.X`) that break inside Docker
- Missing packages in `requirements.txt`
- A `NOT NULL` column with no default that prevented experiment rows from being inserted

---

## Project Structure

Final layout after all changes. Files at root level were moved into `app/` as required by the package import system.

```
soft/                                  ← project root
├── docker-compose.yml                 
├── Dockerfile                         # ★ NEW
├── schema.sql                         
├── wsgi.py                            # ★ NEW
├── requirements.txt                   
├── .env.example                       # ★ NEW
└── app/
    ├── __init__.py                     
    ├── auth.py                         
    ├── db.py                           
    ├── home.py                         
    ├── uniprot.py                      
    ├── FASTA_upload.py                 
    ├── experiment_upload.py           
    ├── analysis.py                    # → (unchanged)
    ├── sequence_processor.py          # → (unchanged)
    ├── FASTA_parsing_logic.py         # → (unchanged)
    ├── parse_data.py                  # → (unchanged)
    ├── qc.py                          # → (unchanged)
    ├── feedback.py                    # → (unchanged)
    ├── uniprotAPI.py                  # → (unchanged)
    ├── uniprot_classes.py             # → (no longer imported)
    └── templates/
        ├── base.html                  # ★ NEW
        ├── home/
        │   ├── index.html             
        │   └── dashboard.html        
        ├── auth/
        │   ├── login.html            
        │   └── register.html         
        ├── uniprot/
        │   ├── uniprot_search.html    
        │   └── uniprot_review.html   
        ├── staging/
        │   ├── plasmid_upload.html   
        │   └── experiment_upload.html 
        └── analysis/
            └── results.html         
```

---

## Detailed Changes

### `docker-compose.yml` 

The original file only defined a `db` service. There was no container definition for the Flask application, so `docker compose up --build` would start Postgres but never the app.

**Added:**
- `app` service that builds from the `Dockerfile`
- `DATABASE_URL` and `SECRET_KEY` passed as environment variables
- `depends_on` with `condition: service_healthy` so the app waits for Postgres before starting
- `healthcheck` on `db` using `pg_isready`
- `uploads/` bind mount so uploaded files survive container restarts
- Host port changed to `8080:5000` 

> **Why 8080?** macOS reserves port 5000 for AirPlay Receiver by default. The container still listens on 5000 internally; only the host-side binding changes.

---

### `Dockerfile` 

No Dockerfile existed. Without it `docker compose up --build` has nothing to build.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p uploads/plasmids uploads/experiments
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
```

---

### `wsgi.py` 

Gunicorn needs a `module:callable` entry point. Without `wsgi.py` the `CMD` in the Dockerfile cannot resolve the application object.

```python
from app import create_app
app = create_app()
```

---

### `requirements.txt`

| Package |
|---|---|
| `flask>=3.0` 
| `psycopg[binary]` 
| `biopython` 
| `werkzeug` 
| `gunicorn`
| `flask-login` 
| `flask-wtf`
| `requests` 

---

### `schema.sql` 

One column definition caused every `INSERT` to the `experiments` table to fail.

```sql
-- Before
wt_dna_sequence TEXT NOT NULL,

-- After
wt_dna_sequence TEXT NOT NULL DEFAULT '',
```

The column was `NOT NULL` with no default, but the app only populates it *after* the plasmid upload step. The `INSERT` during UniProt data storage would fail with a `NOT NULL` constraint violation.

---

### `app/__init__.py` (merged)

Two separate `__init__.py` files existed, each representing a different development branch. Neither was complete.

**The new file:**
- Registers all blueprints in one factory function
- Wires up Flask-Login with a psycopg-based `user_loader`
---

### `app/db.py` 

`db.py` imported both `psycopg` and `flask_sqlalchemy`, initialising two separate database engines. Different modules expected different DB objects, causing `RuntimeError` at startup.

**Changes:**
- Removed `SQLAlchemy` import and `db = SQLAlchemy()` instance entirely
- Kept only psycopg connection logic with `dict_row` factory
- All modules now call `get_db()` consistently

---

### `app/auth.py` 

Rewritten from `auth.py`. Behaviour is identical; only the database layer changes.

- Replaced SQLAlchemy session queries with raw `psycopg` cursor calls
- `User(UserMixin)` class preserved exactly
- Register, login, and logout routes unchanged in behaviour

---

### `app/home.py` 

The original `home.py` had only a bare `index` route. `home.py` had the correct authenticated dashboard. The new file combines both:

- `index()` redirects authenticated users to `/dashboard`
- `dashboard()` protected with `@login_required`
- Passes `current_user` to the template

---

### `app/uniprot.py`

#### Problem 1 — `data_stored()` did not write to the database

```python
# Original
@bp.route("/data-stored")
def data_stored():
    ...
    db.session.add(protein)
    db.session.commit()
    return 'UPLOAD PLASMID'   # ← string, experiment_id never set in session
```

Because `experiment_id` was never placed in the session, every downstream route (`/plasmid_upload`, `/experiment_upload`, `/analysis`) would fail silently or raise a `KeyError`.

#### Problem 2 — SQLAlchemy ORM not initialised

The route used `UniprotProtein` and `UniprotFeatures` ORM models, but `SQLAlchemy` was not initialised in the app factory. All `db.session` calls raised `RuntimeError: No application found`.

#### What changed

- `data_stored()` now `INSERT`s into `experiments` via raw SQL using `get_db()`
- Sets `session['experiment_id']` after the insert
- Sets `session['validated'] = False` to enforce the plasmid upload step
- Redirects to `/plasmid_upload/` instead of returning a string
- Route URL changed from `/data-stored` to `/store`
- `uniprot_review.html` "Store Data" button updated to match new route name
- All SQLAlchemy ORM imports removed; `uniprot_classes.py` no longer imported anywhere

---

### `app/FASTA_upload.py`

```python
# Before — absolute imports break inside Docker
from app.FASTA_parsing_logic import parse_file as parse_fasta, validate_protein
from app.db import get_db

# After — relative imports
from .FASTA_parsing_logic import parse_file as parse_fasta, validate_protein
from .db import get_db
```

**Additional fixes:**
- `uniprot_id` now passed to `render_template()` (it was referenced in the template but never passed by the route, causing a `NameError`)
- On successful validation, `UPDATE experiments SET wt_dna_sequence` to persist the plasmid sequence to the DB
- Removed the unused `/staging` redirect route
- Added `@login_required`

---

### `app/experiment_upload.py`

```python
# Before
from app.parse_data import parse_data
from app.qc import validate_data
from app.feedback import build_feedback, error_feedback
from app.db import get_db

# After
from .parse_data import parse_data
from .qc import validate_data
from .feedback import build_feedback, error_feedback
from .db import get_db
```

Absolute imports (`from app.X`) break when the package is run from inside a Docker container because the working directory is `/app`, causing Python to look for a nested `app.app` package.

---

### Templates

A shared `base.html` was created providing the navigation bar, flash message rendering, and CSS so all pages have a consistent layout.

| Template | Key changes vs original |
|---|---|
| `base.html` | Created — shared nav, flash messages, CSS, `current_user` awareness |
| `home/index.html` | Extends `base.html`; register/login buttons |
| `home/dashboard.html`|
| `auth/login.html` | Extends `base.html` |
| `auth/register.html` | Extends `base.html` |
| `uniprot/uniprot_search.html` | Extends `base.html`; WTForms rendering preserved |
| `uniprot/uniprot_review.html` | "Store Data" link updated from `data_stored` → `store` route |
| `staging/plasmid_upload.html` | Added `{{ uniprot_id }}` display (variable was referenced but not passed) |
| `staging/experiment_upload.html` | Extends `base.html`; shows inserted row count |
| `analysis/results.html` | Extends `base.html`; table logic preserved from original |

---

## Bug Summary

| # | Bug | Impact | Fix |
|---|---|---|---|
| 1 | No `Dockerfile` or app service in `docker-compose.yml` | App never starts | Created both |
| 2 | No `wsgi.py` | Gunicorn cannot find the app object | Created `wsgi.py` |
| 3 | Two `__init__.py` files, neither complete | Blueprints missing| Merged|
| 4 | SQLAlchemy mixed with psycopg | `RuntimeError` on all ORM DB calls | Removed SQLAlchemy entirely |
| 5 | `data_stored()` returned a string, no DB write | `experiment_id` never in session | Rewrote to `INSERT` + redirect |
| 6 | Absolute imports (`from app.X`) | `ModuleNotFoundError` inside Docker | Changed to relative imports |
| 7 | `wt_dna_sequence NOT NULL` with no default | Experiment `INSERT` fails | Added `DEFAULT ''` |
| 8 | `uniprot_id` not passed to plasmid template | `NameError` / blank display | Added to `render_template()` call |
| 9 | "Store Data" URL pointed to old route name | 404 on confirmation page | Updated to `/store` |
| 10 | `flask-login`, `flask-wtf`, `requests` missing | `ImportError` on startup | Added to `requirements.txt` |

---

## Application Flow

```
Register → Login → Dashboard
                       ↓
              Search UniProt ID (/uniprot/)
                       ↓
              Review protein + features
                       ↓
              Confirm & Store → experiment row created, experiment_id set in session
                       ↓
              Upload plasmid FASTA (/plasmid_upload/)
              [validates WT protein is found in plasmid]
                       ↓
              Upload experiment data (/experiment_upload/)
              [.json or .tsv with variant sequences + measurements]
                       ↓
              Run Step 1 ORF Analysis
                       ↓
              Results table (/analysis/results/experiment/<id>)
```

---

## How to Run

```bash
# Start everything
docker compose up --build

# App is available at:
# http://localhost:8080

# Stop (keep database volume)
docker compose down

# Stop and delete all data
docker compose down -v

# View logs
docker compose logs app   # Flask / gunicorn
docker compose logs db    # PostgreSQL
```
