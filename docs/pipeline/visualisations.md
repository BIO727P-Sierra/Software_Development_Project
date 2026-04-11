# Visualisations

Three visualisations are available once the analysis step has been completed and activity scores have been calculated. All plots are accessible from the experiment results page.

| Visualisation | Route | Output |
|---|---|---|
| Generation Activity Box Plot | `/analysis/results/experiment/activity_per_generation_graph/<experiment_id>` | Base64 PNG embedded in template |
| Mutation Fingerprint | `/analysis/results/experiment/<experiment_id>/top-performers` | Static PNG image |
| Activity Landscape | `/visualisation/landscape/<experiment_id>` | Interactive Plotly HTML (3D surface) |

---

## Generation Activity Box Plot

The boxplot provides an overview of activity score per generation of variants in the current experiment, allowing data across different generations to be compared. Users can show or hide outliers in the boxplot.

### User workflow

Following the completion of activity score calculation, the user can view the boxplot from the results page. The boxplot is encoded as a base64 PNG embedded into the HTML.

### Data preprocessing

Generation and activity score data are retrieved from the database where `activity_score IS NOT NULL`, ordered by generation. The data is compiled into a single dictionary, and Matplotlib is used to plot the boxplot, save it as PNG, and encode it as base64 to be embedded into HTML.

---

## Mutation Fingerprint (Bonus Visualisation)

The mutation fingerprint visualises the top 10 variants from generations 1 through 10 and the specific amino acid substitutions that were introduced across successive generations of the directed evolution experiment. Each variant's lineage is traced by `parent_variant_id`, aligning every child protein sequence to its parent using global pairwise alignment (Biopython `PairwiseAligner`). The final plot shows the full parent–child lineage of a selected variant, identifies the specific substitutions introduced in each generation, and plots the mutations along the linear WT protein sequence.

### User workflow

Once the experiment runs successfully, the user navigates to the Top 10 Performing Variants table. From a dropdown menu showing the top 10 variants, the user selects a variant of interest; the plot is automatically created and displayed beneath the table on the same page.

### Data retrieval and lineage reconstruction

The mutation fingerprinting process begins by reconstructing the full evolutionary lineage of the selected variant, implemented in `get_lineage()`, which follows the `parent_variant_id` chain until the root variant is reached. For each variant, the retrieved fields are `variant_id`, `generation`, `parent_variant_id`, `orf_protein_sequence`, and `wt_protein_sequence`. The lineage is then reversed to produce a chronological order from the WT ancestor to the selected variant.

### Mutation extraction by pairwise alignment

For each generation, the amino acid substitutions introduced relative to the previous generation are identified, implemented by `get_generation_mutations()` and `get_pairwise_mutations()`.

**Alignment strategy (global alignment)** — Global alignment is performed between the child protein sequence and its parent (the WT for generation 0) using Biopython's `PairwiseAligner`, the same aligner used in ORF analysis. The parameters are: match `+1`, mismatch `-1`, gap open `-2`, gap extend `-0.5`. The plot displays substitutions; indels are ignored.

**Mutation representation** — Each mutation is stored with `position`, `wt`, `mut` (mutant residue), `generation` (generation the mutation first appeared), and `label`.

### Plot features

The mutation fingerprint visualisation is generated in `finger_print_plot()` using Matplotlib with the non-interactive `Agg` backend for rendering.

- The horizontal line represents the protein backbone (WT protein sequence).
- Each mutation is plotted as a coloured marker above its residue position; the y-axis represents the generation in which the mutation was introduced.
- Vertical lines connect each mutation marker to the backbone.
- Each marker displays the label of the mutation.
- A legend maps colours to generations.

If a variant has no detectable lineage mutations, a placeholder figure is returned with the message *"No lineage mutations found"*.

### Error handling

| Condition | Behaviour |
|---|---|
| Invalid variant ID | Returns HTTP 404 |
| Lineage cannot be reconstructed | Returns `(None, [], None)` and 404 |
| Variant has no protein sequence | No mutations are extracted and placeholder plot returned |
| No mutations detected across lineage | Returns message *"No lineage mutations found"* |
| Alignment failure | Empty mutation list and placeholder plot returned |
| Indels detected | Substitutions are plotted, indels ignored |
| Missing WT protein sequence | Protein length defaults to maximum mutation position and plot still generated |
| Unexpected database error | Lineage reconstruction stops, variant treated as having no mutations |

### References

| Source | Used for |
|---|---|
| Yang K. K., Wu Z. (2019). *Machine-learning-guided directed evolution.* Nature Methods | Tracking mutations and analysing how substitutions accumulate across evolutionary rounds |
| Starr T. N., Thornton J. W. (2016). *Epistasis in protein evolution.* | Mapping mutations onto protein sequences; understanding how individual substitutions contribute to evolutionary pathways |
| Cock P. J. A. et al. (2009–2023). *Biopython.* Bioinformatics | `PairwiseAligner` |
| Lau et al. (2021). *Profiling SARS-CoV-2 mutation fingerprints from the viral pangenome to individual infection quasispecies.* | Inspiration for the mutation fingerprint plot style |

---

## Activity Landscape (Bonus Visualisation)

The activity landscape provides a global view of the sequence relationships across all variants in a user's experiment. Each variant is represented as a plot point in a reduced two-dimensional space, with the activity score per variant mapped on the third dimension (z-axis). The resulting topographical surface allows areas of high and low activity to be visually identified.

### User workflow

Following the completion of activity score calculation, the user can view the activity landscape from the results page. The plot is rendered as an interactive 3D surface, allowing zooming and inspection of individual data points. Variant data are displayed as discrete scatter points to pinpoint activity scores, with a continuous surface to show overall trends.

### Data preprocessing

Variant data is retrieved from the database, filtered by `experiment_id` via an SQL query. Only variants with a non-null activity score are retrieved to ensure meaningful data is plotted.

The result is converted into a Pandas DataFrame for simpler processing. Records with missing or empty sequences are filtered out to prevent downstream failures. To limit rendering time and prevent computational overload, the dataset is subsampled to a maximum of 2000 entries when needed. This subsampling ensures an accurate reflection of the overall sequence space while keeping the visualisation responsive.

### Sequence encoding

Protein sequences are transformed into numerical vectors using amino acid frequencies, with the encoding scheme using the standard amino acid alphabet to correspond to a vector.

For each sequence, the frequency of each amino acid is counted and normalised by sequence length to produce a compact representation of the whole sequence composition. This encoding avoids high-dimensional positional encodings while still capturing relationships between sequences.

### PCA / dimensionality reduction

The encodings are standardised using scikit-learn's `StandardScaler` to ensure an equal contribution of amino acid frequencies in the downstream analysis (removing the means and scaling to unit variance).

Principal Component Analysis (PCA) is then applied to reduce the 20-dimensional feature space (one dimension per amino acid) down to two principal components. These represent the directions of greatest variance across the dataset, effectively capturing sequence similarity.

Each variant receives coordinates `(PC1, PC2)` defining where it is plotted in 2D space. Variants with similar amino acid compositions tend to cluster together, while more diverse sequences are placed further apart.

### Landscape and visualisation

A grid is constructed over the PCA coordinates using `scipy.interpolate.griddata` to generate a continuous activity surface, where activity scores are linearly interpolated across the space. This allows the visualisation of peaks and gradients in activity scores.

The scatter layer plots the individual data points with marker colours corresponding to the activity score. The surface topographical layer is coloured using a heatmap scale of interpolated activity scores. The x-axis (PC1) is the first principal component, the y-axis (PC2) is the second principal component, and the z-axis is the activity score.

Clusters of high-activity variants produce peaks in the landscape, and low-activity regions create valleys. The gradients indicate evolutionary trajectories across sequence variants. However, the landscape depicts broad similarities rather than exact mutational pathways, as it is based on global amino acid composition rather than positional alignment.

### Error handling

| Condition | Behaviour |
|---|---|
| No variants with activity scores | Returns *"No activity data available"* |
| No valid protein sequences | Returns error message |
| Protein encoding failure | Returns error message |
| Empty dataset after filtering | The plot is not generated |
