import pandas as pd
import numpy as np
import plotly.graph_objects as go

from sklearn.manifold import TSNE
from scipy.interpolate import griddata
from flask import Blueprint, render_template
from flask_login import login_required

from .db import get_db

# This page requires mutations and activity score pages!

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

    df = pd.DataFrame(
        rows,
        columns=["variant_id", "protein_sequence", "activity_score"])

    return df

# Encoding the proteins
amino_acids = "ARNDCEQGHILKMFPSTWYV" # Letters of aminoacids

def encode_sequence(sequence, max_length):

    sequence = sequence.ljust(max_length, "-")
    
    encoded_proteins = []

    for aa in sequence:

        if aa in amino_acids:
            vector = [1 if aa == x else 0 for x in amino_acids]
        else:
            vector = [0]*len(amino_acids)
        
        encoded_proteins.extend(vector)

    return encoded_proteins

def generate_landscape(experiment_id):

    df = get_variants(experiment_id)

    if df.empty:
        return "<p>No activity data available.</p>"
    
    # Remove any sequences that may be empty
    df = df[df["protein_sequence"].notna()]
    df = df[df["protein_sequence"].astype(str).str.len() > 0]

    # Error for is all sequences are empty
    if df.empty:
        return "<p>No valid protein sequences found.</p>"

    # Finding longest sequence
    max_length = df["protein_sequence"].str.len().max()

    encoded_sequences = df["protein_sequence"].apply(lambda seq: encode_sequence(seq, max_length))
    
    X = np.array(encoded_sequences.to_list())

    if X.shape[1] == 0:
        return "<p>Encoding failed.</p>"
    
    tsne = TSNE(n_components=2, perplexity=30, random_state=42)
    components = tsne.fit_transform(X)

    df["x"] = components[:, 0]
    df["y"] = components[:, 1]

    # Creating the grids
    grid_x, grid_y = np.mgrid[df.x.min():df.x.max():100j, df.y.min():df.y.max():100j]

    grid_z = griddata(
        (df.x, df.y),
        df.activity_score,
        (grid_x, grid_y),
        method="cubic"
    )

    # Creating the plot topographical surface
    fig = go.Figure()

    fig.add_trace(
        go.Surface(
            x=grid_x,
            y=grid_y,
            z=grid_z,
            colorscale="YlOrRd",
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
            xaxis_title = "Sequence Diversity (t-SNE 1)",
            yaxis_title = "Sequence Diversity (t-SNE 2)",
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
