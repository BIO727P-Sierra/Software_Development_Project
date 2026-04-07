# generation_plot.py
import matplotlib.pyplot as plt
import base64
import io
import numpy as np

def plot_boxplot(data_dict, showoutlier):
    # Create boxplot for activity score per generation

    fig = plt.figure(figsize=(16, 8))
    ax = fig.add_subplot(111)
    bp = ax.boxplot(
        data_dict.values(),
        labels=data_dict.keys(),
        patch_artist=True,
        showfliers=showoutlier,
        vert=0)
    colors = plt.cm.tab10(np.linspace(0, 1, len(data_dict.keys())))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    for whisker in bp['whiskers']:
        whisker.set(color="#000000",
                    linewidth=1.5,
                    linestyle=":")
    for cap in bp['caps']:
        cap.set(color="#000000",
                linewidth=2)
    for median in bp['medians']:
        median.set(color='#000000',
                   linewidth=1.5)
    for flier in bp['fliers']:
        flier.set(marker='D',
                  color='#e7298a',
                  alpha=0.5)

    ax.set_xlabel("Unified Activity Score", fontsize=16, fontweight='bold', labelpad=12)
    ax.set_ylabel("Generation", fontsize=16, fontweight='bold', labelpad=12)
    ax.set_title("Activity Score Distribution per Generation", fontsize=20, fontweight='bold', pad=16)
    ax.tick_params(axis='both', labelsize=14)

    fig.tight_layout()

    # Save plot at high DPI
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=150, bbox_inches='tight')
    plt.close()
    img.seek(0)

    # Encode to base64
    plot_url = base64.b64encode(img.getvalue()).decode()

    return plot_url
