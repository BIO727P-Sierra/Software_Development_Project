# generation_plot.py
import matplotlib.pyplot as plt
import base64
import io
import numpy as np

def plot_boxplot(data_dict, showoutlier):
    # Create boxplot for activity score per generation

    fig = plt.figure(figsize=(8,4))
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
        whisker.set(color ="#000000",
                    linewidth = 1.5,
                    linestyle =":")
    for cap in bp['caps']:
        cap.set(color ="#000000",
                linewidth = 2)
    for median in bp['medians']:
        median.set(color ='#000000',
                linewidth = 1)
    for flier in bp['fliers']:
        flier.set(marker ='D',
                color ='#e7298a',
                alpha = 0.5)
    ax.set_xlabel("Generation")
    ax.set_ylabel("Unified Activity Score")
    
    # Save plot 
    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)

    # Encode to base64
    plot_url = base64.b64encode(img.getvalue()).decode()

    return plot_url
