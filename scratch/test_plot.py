import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Mock data
time_s = np.linspace(0, 10, 100)
data = np.zeros(100)
data[20:40] = 1
data[70:80] = 2

df = pd.DataFrame({'time': time_s, 'col': data})

fig, ax = plt.subplots(facecolor='#1e1e1e')
ax.set_facecolor('#121212')

# Simulating the plot for a flag parameter
ax.set_yticks([])
ax.set_yticklabels([])
ax.spines['left'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)

ax.set_ylim(0, 1)

# Top half time axis markers
changes = df['col'] != df['col'].shift(1)
change_times = df['time'][changes]
ax.plot(change_times, [0.8] * len(change_times), marker='d', linestyle='None', color='#00ee66', markersize=5, zorder=3, alpha=0.8)

# Cover the bottom half
ax.axhspan(0, 0.6, facecolor='#121212', edgecolor='none', zorder=10)
ax.axhline(0.6, color='#333333', linewidth=1, zorder=11, alpha=0.5)

# Add tags
txt = ax.text(0.1, 0.3, "TAG 1", ha="left", va="center",
              transform=ax.transAxes,
              bbox=dict(boxstyle="round,pad=0.4", fc="#333333", ec="none"),
              color="#888888", fontsize=10, weight='bold', zorder=12)

# Grid and cursor line
ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
ax.axvline(5, color='white', linestyle='-', alpha=0.8, linewidth=1.5, zorder=5)

fig.savefig('scratch/test_plot.png')
