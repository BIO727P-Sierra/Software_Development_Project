import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
import string


from sklearn.decomposition import PCA
from scipy.interpolate import griddata


# Encoding the proteins
amino_acids = "ARNDCEQGHILKMFPSTWYV" # Letters of aminoacids

N = 50
seq_length = 30

def random_protein_sequence(length):
    return ''.join(random.choice(amino_acids) for _ in range(length))

data = []
for i in range(N):
    seq = random_protein_sequence(seq_length)
    score = random.uniform(0, 100)
    data.append({"variant_id": i+1, "protein_sequence": seq, "activity_score": score})

df = pd.DataFrame(data)

max_length = df["protein_sequence"].str.len().max()

def encode_sequence(sequence, max_length):

    sequence = sequence.ljust(max_length, "-")
    encoded_proteins = []
    for aa in sequence:
        vector = [1 if aa == x else 0 for x in amino_acids]
        encoded_proteins.extend(vector)

    return encoded_proteins

encoded_sequences = df["protein_sequence"].apply(lambda seq: encode_sequence(seq, max_length))
    
X = np.array(encoded_sequences.to_list())
 
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
    title="3D Activity Landscape", 
    scene=dict(
        xaxis_title = "Sequence Diversity (PC1)",
        yaxis_title = "Sequence Diversity (PC2)",
        zaxis_title = "Activity Score"
    )
)

fig.show()

fig.write_html("test_fake_activity_landscape")