import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from Bio.Align import PairwiseAligner
from flask import Blueprint, send_file, abort

from .db import get_db


fingerprint_bp = Blueprint("fingerprint", __name__, url_prefix="/fingerprint")


@fingerprint_bp.route("/<int:variant_id>")
def mutation_fingerprint(variant_id):
    fig = finger_print_plot(variant_id)
    img = io.BytesIO()
    fig.savefig(img, format="png", bbox_inches="tight", dpi=200)
    img.seek(0)
    plt.close(fig)
    return send_file(img, mimetype="image/png")


def get_variant_row(cur, variant_id):
    cur.execute(
        """
        SELECT
            v.variant_id,
            v.experiment_id,
            v.parent_variant_id,
            v.generation,
            v.plasmid_variant_index,
            v.orf_protein_sequence,
            e.wt_protein_sequence
        FROM variants v
        JOIN experiments e
          ON e.experiment_id = v.experiment_id
        WHERE v.variant_id = %s
        """,
        (variant_id,),
    )
    return cur.fetchone()


def get_lineage(variant_id):
    """
    Return lineage from root -> selected variant.
    """
    db = get_db()
    lineage = []

    with db.cursor() as cur:
        current = variant_id

        while current:
            row = get_variant_row(cur, current)
            if not row:
                break

            lineage.append(
                {
                    "variant_id": row["variant_id"],
                    "experiment_id": row["experiment_id"],
                    "parent_variant_id": row["parent_variant_id"],
                    "generation": row["generation"],
                    "plasmid_variant_index": row["plasmid_variant_index"],
                    "protein_sequence": row["orf_protein_sequence"],
                    "wt_protein_sequence": row["wt_protein_sequence"],
                }
            )
            current = row["parent_variant_id"]

    lineage.reverse()
    return lineage


def get_pairwise_mutations(child_seq: str, parent_seq: str):
    """
    Compare child protein to parent protein and return substitutions only.
    """
    if not child_seq or not parent_seq:
        return []

    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 1
    aligner.mismatch_score = -1
    aligner.open_gap_score = -2
    aligner.extend_gap_score = -0.5

    try:
        aligner.max_number_of_alignments = 1
    except Exception:
        pass

    try:
        aln = next(iter(aligner.align(child_seq, parent_seq)))
    except StopIteration:
        return []

    aligned_child, aligned_parent = aln

    mutations =[]
    parent_pos = 0

    for c, p in zip(aligned_child, aligned_parent):
        if p != "-":
            parent_pos += 1

        # ignore indels for now
        if c == "-" or p == "-":
            continue

        if c != p:
            mutations.append(
                {
                    "position": parent_pos,
                    "wt": p,
                    "mut": c,
                }
            )

    return mutations

### get_lineage reconstructs the genes using parent_variant_id ###

### get_generation_mutations() compares each variant's orf_protein_sequence to parent sequence

def get_generation_mutations(variant_id):
    """
    Walk through the lineage and record which substitutions were introduced
    at each generation.
    """
    lineage = get_lineage(variant_id) 
    if not lineage:
        return None, [], None

    wt_seq = lineage[0]["wt_protein_sequence"]
    protein_length = len(wt_seq) if wt_seq else None

    events = []

    for i, node in enumerate(lineage):
        child_seq = node["protein_sequence"]
        if not child_seq:
            continue

        if i == 0:
            parent_seq = wt_seq
        else:
            parent_seq = lineage[i - 1]["protein_sequence"] or wt_seq

        muts = get_pairwise_mutations(child_seq, parent_seq)

        for m in muts:
            events.append(
                {
                    "generation": node["generation"],
                    "position": m["position"],
                    "wt": m["wt"],
                    "mut": m["mut"],
                    "label": f"{m['wt']}{m['position']}{m['mut']}",
                }
            )

    return lineage[-1], events, protein_length


def finger_print_plot(variant_id):
    selected_variant, mutations, protein_length = get_generation_mutations(variant_id)

    if selected_variant is None:
        abort(404)

    if not mutations:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.text(
            0.5,
            0.5,
            "No lineage mutations found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return fig

    unique_gens = sorted(set(m["generation"] for m in mutations))
    cmap = plt.cm.tab10
    gen_colour = {gen: cmap(i % 10) for i, gen in enumerate(unique_gens)}

    fig, ax = plt.subplots(figsize=(14, 4))

    backbone_length = protein_length if protein_length else max(m["position"] for m in mutations) + 10

    # protein backbone
    ax.hlines(y=0.35, xmin=1, xmax=backbone_length, linewidth=6, color="lightgray")
    ax.hlines(y=0.35, xmin=1, xmax=backbone_length, linewidth=1.5, color="black")

    y_levels = [0.55, 0.68, 0.81]

    for idx, m in enumerate(sorted(mutations, key=lambda x: (x["position"], x["generation"]))):
        x = m["position"]
        y = y_levels[idx % len(y_levels)]
        color = gen_colour[m["generation"]]

        ax.scatter(
            x,
            y,
            s=90,
            color=color,
            edgecolors="black",
            linewidths=0.8,
            zorder=3,
        )

        ax.plot([x, x], [0.38, y - 0.03], color="gray", linewidth=0.8, zorder=2)

        ax.text(
            x,
            y + 0.05,
            m["label"],
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=45,
        )

    ax.set_xlim(0, backbone_length + 10)
    ax.set_ylim(0.2, 1.0)
    ax.set_yticks([])
    ax.set_xlabel("Amino acid position")
    ax.set_title(
        f"Mutation fingerprint – Variant ID {selected_variant['variant_id']}", pad = 20
    )

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=gen_colour[g],
            markeredgecolor="black",
            markersize=8,
            label=f"Generation {g}",
        )
        for g in unique_gens
    ]
    ax.legend(handles=legend_elements, loc= "upper center", title="Lineage Generations", bbox_to_anchor=(0.5, -0.35), ncol = 3,)
    
    for spine in ["left", "right", "top"]:
        ax.spines[spine].set_visible(False)
    
    fig.tight_layout()




    return fig
