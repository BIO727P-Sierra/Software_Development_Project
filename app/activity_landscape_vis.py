import pandas as pd
import numpy as np
import plotly.graph_objects as go

from sklearn.decomposition import PCA
from scipy.interpolate import griddata
from flask import Blueprint, render_template
from flask_login import login_required

from .db import get_db

# Retrieving variables from the database
def get_variants():
    
    db = get_db()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                variant_id,
                protein_sequence,
                activity_score
            FROM variants
            WHERE activity_score IS NOT NULL
            """
        )

        rows = cur.fetchall()

    df = pd.DataFrame(rows)

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

def generate_landscape():

    df = get_variants()

    if df.empty:
        return "<p>No activity data available.</p>"
    
    # Remove any sequences that may be empty
    df = df[df["protein_sequence"].notna()]
    df = df[df["protein_sequence"] != ""]

    # Error for is all sequences are empty
    if df.empty:
        return "<p>No valid protein sequences found.</p>"

    # Finding longest sequence
    max_length = df["protein_sequence"].str.len().max()

    encoded_sequences = df["protein_sequence"].apply(lambda seq: encode_sequence(seq, max_length))
    
    X = np.array(encoded_sequences.to_list())

    if X.shape[1] == 0:
        return "<p>Encoding failed.</p>"
    
    # PCA reducing dimensionality
    pca = PCA(n_components = 2)
    components = pca.fit_transform(X)

    df["x"] = components[:,0]
    df["y"] = components[:,1]

    # Creating the grids
    grid_x, grid_y = np.mgrid[df.x.min():df.x.max():100j, df.y.min():df.y.max():100j]

    grid_z = griddata(
        (df.x, df.y),
        df.activity_score,
        (grid_x, grid_y),
        method="linear"
    )

    # Creating the plot topographical surface
    fig = go.Figure(data=[go.Surface(x=grid_x, y=grid_y, z=grid_z)])

    fig.update_layout(
        title=dict(
            text="3D Activity Landscape"), 
                autosize=False,
                scene=dict(
                    xaxis_title = "Sequence Diversity (PC1)",
                    yaxis_title = "Sequence Diversity (PC2)",
                    zaxis_title = "Activity Score"
                )
    )

    return fig.to_html(full_html=False)

# Flask route    
bp = Blueprint("visualisation", __name__, url_prefix="/visualisation")

@bp.route("/landscape")
@login_required
def landscape():
    plot_html = generate_landscape()

    return render_template(
        "visualisation/activity_landscape.html",
        plot_html=plot_html
    )