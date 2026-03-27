import pandas as pd
import numpy as np
import plotly.graph_objects as go

from scipy.interpolate import griddata
from flask import Blueprint, render_template
from flask_login import login_required
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .db import get_db

# Retrieving variables from the database
def get_variants(experiment_id):
    
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                variant_id,
                assembled_dna_sequence AS protein_sequence,
                activity_score
            FROM variants
            WHERE experiment_id = %s
            AND activity_score IS NOT NULL
            """,
            (experiment_id,)
        )

        rows = cur.fetchall()

    # Converting SQL result into a Dataframe, easier to manipulate the data this way
    df = pd.DataFrame(
        rows,
        columns=["protein_sequence", "activity_score"])
    
    # Remove any sequences that may be empty
    df = df[df["protein_sequence"].notna()]
    df = df[df["protein_sequence"].astype(str).str.len() > 0]

    return df

# Encoding the proteins based on frequency
amino_acids = "ARNDCEQGHILKMFPSTWYV" # Letters of aminoacids

def encode_sequences(sequences):
    n = len(sequences)

    # Preallocate compact array
    X = np.zeros((n, len(amino_acids)), dtype=np.float32)

    for i, seq in enumerate(sequences):
        for aa in seq:
            idx = {aa: i for i, aa in enumerate(amino_acids)}.get(aa)
            if idx is not None:
                X[i, idx] += 1
        if len(seq) > 0:
            X[i] /= len(seq)

    return X

# Generating landscape, X and Y represent sequence similarity and Z the activity score
def generate_landscape(experiment_id):

    df = get_variants(experiment_id)

    if df.empty:
        return "<p>No activity data available.</p>"
    
    # Error for is all sequences are empty
    if df.empty:
        return "<p>No valid protein sequences found.</p>"
    
    max_samples = 2000
    if len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)

    sequences = df["protein_sequence"].values

    # More memory efficient coding
    X = encode_sequences(sequences)

    if X.shape[1] == 0:
        return "<p>Encoding failed.</p>"
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Performing PCA, reducing dimensionality and allow clustering
    pca = PCA(n_components=2, random_state=42)
    components = pca.fit_transform(X_scaled)

    df["x"] = components[:, 0]
    df["y"] = components[:, 1]

    # Creating the grids with activity score
    grid_x, grid_y = np.mgrid[df.x.min():df.x.max():40j, df.y.min():df.y.max():40j]

    grid_z = griddata(
        (df.x, df.y),
        df.activity_score,
        (grid_x, grid_y),
        method="linear"
    )

    # Creating the plot topographical surface
    fig = go.Figure()

    fig.add_trace(
        go.Surface(
            x=grid_x,
            y=grid_y,
            z=grid_z,
            colorscale="YlOrRd", # Heat map
            opacity=0.8
        )
    )

    # Activity score scatter points
    fig.add_trace(
        go.Scatter3d(
            x=df["x"],
            y=df["y"],
            z=df["activity_score"],
            mode="markers",
            marker=dict(size=2, color=df["activity_score"], colorscale="RdBu", opacity=0.5)
        )
    )

    fig.update_layout(
        title = "3D Activity Landscape",
        scene=dict(
            xaxis_title = "Sequence Diversity (PC1)",
            yaxis_title = "Sequence Diversity (PC2)",
            zaxis_title = "Activity Score"
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig.to_html(full_html=False)

# Flask route    
bp = Blueprint("visualisation", __name__, url_prefix="/visualisation")

@bp.route("/landscape/<int:experiment_id>")
@login_required
def landscape(experiment_id):
    plot_html = generate_landscape(experiment_id)

    return render_template(
        "visualisation/activity_landscape.html",
        plot_html=plot_html,
        experiment_id=experiment_id
    )
