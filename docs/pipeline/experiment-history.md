# Experiment History

The portal provides a persistent experiment history feature that allows the user to save, view, rename, and delete past experiments. Saved experiments are accessible at any time from the dashboard and/or navigation bar, providing a centralised record of all completed user-specific directed evolution campaigns for later reference.

---

## For scientists

### User workflow

Following the completion of analysis, the user can save the experiment by clicking the **Save Experiment** button on the results page. Once saved, the experiment will appear on the **Past Experiments** page, from where the user can:

- **View** the full experiment results
- **Download** a summary report in PDF format
- **Rename** the experiment
- **Delete** it permanently

Upon logging in, the user can also access past experiments via the **View Past Experiments** button on the home page.

### PDF report download

A PDF summary report can be downloaded for any saved experiment via the **Download Report** button. The report is generated on demand using ReportLab and is never written to disk — it is streamed directly to the browser as a file download.

The report contains four sections:

1. **Experiment metadata** — name, UniProt ID, creation and save dates, wild-type protein sequence preview
2. **Analysis summary** — total variants, ORF status, activity score statistics
3. **Per-generation breakdown** — one table row per generation
4. **Top 10 performing variants** — highest-scoring variant highlighted

The report requires `reportlab` to be installed, which is included in `requirements.txt`.

---

## For developers

### Routes

| Method | URL | Handler |
|---|---|---|
| `GET` | `/experiments/` | `past_experiments.list_experiments` |
| `POST` | `/experiments/save/<experiment_id>` | `past_experiments.save_experiment` |
| `POST` | `/experiments/rename/<experiment_id>` | `past_experiments.rename_experiment` |
| `POST` | `/experiments/delete/<experiment_id>` | `past_experiments.delete_experiment` |
| `GET` | `/report/experiment/<experiment_id>` | `report.download_report` |

### Saving an experiment

An experiment is saved by stamping a `saved_at` timestamp on the experiment row. Only experiments with a non-NULL `saved_at` value appear in the Past Experiments list. This reduces clutter and saves experiments only when the user explicitly requests it.

### Renaming an experiment

The experiment name defaults to `"Experiment – {uniprot_id}"` at creation. Users may assign a more descriptive label at any time via the **Rename** function, which opens an inline modal on the Past Experiments page. The updated name is written to the `experiment_name` column of the `experiments` table. Names are validated to be non-empty and no longer than 255 characters.

### Deleting an experiment

Deleting an experiment permanently removes the experiment row and all associated data. Cascading deletes defined in the schema automatically remove all child rows across the `variants`, `measurements`, and `mutations` tables. A confirmation modal is presented before deletion to prevent accidental data loss, as this action cannot be undone.

### Ownership and access control

All routes perform an ownership check before executing any database operation. If the experiment does not belong to the currently authenticated user, a `403 Forbidden` response is returned, ensuring that users can only view, modify, or delete their own experiments.

### Database column

The feature relies on one additional column on the `experiments` table:

| Column | Type | Description |
|---|---|---|
| `saved_at` | `TIMESTAMP` | Set when the user saves the experiment; `NULL` until saved. Only experiments with a non-NULL `saved_at` appear in the Past Experiments list |

### Error handling

| Condition | Behaviour |
|---|---|
| Experiment not found | `403` returned |
| Experiment belongs to another user | `403` returned |
| Empty or missing rename value | Flash message shown, redirect to list |
| Rename value exceeds 255 characters | Flash message shown, redirect to list |
| No scored variants at report generation | Report generated with explanatory message in place of top performers table |
