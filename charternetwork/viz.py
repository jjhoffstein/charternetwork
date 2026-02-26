import json, numpy as np, matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly
from matplotlib.collections import PatchCollection
from pathlib import Path

COLORS = dict(ferry_naive='#e74c3c', ferry_opt='#2ecc71', revenue='#95a5a6', idle='#bdc3c7', accent='#3498db', bg='#1a1a2e', land='#16213e', border='#0f3460')

def load_states():
    "Load US states GeoJSON"
    with open(Path(__file__).parent.parent / 'data/geo/us_states.json') as f: return json.load(f)

def _draw_states(ax, states):
    "Draw filled state polygons with borders"
    patches = []
    for feat in states['features']:
        geom = feat['geometry']
        polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            ring = np.array(poly[0])
            patches.append(MplPoly(ring, closed=True))
    ax.add_collection(PatchCollection(patches, facecolor=COLORS['land'], edgecolor=COLORS['border'], linewidth=0.5, alpha=0.8))

def _gc_pts(lat1, lon1, lat2, lon2, n=50):
    "Interpolate great circle arc"
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    d = np.arccos(np.clip(np.sin(lat1)*np.sin(lat2) + np.cos(lat1)*np.cos(lat2)*np.cos(lon2-lon1), -1, 1))
    if d < 1e-6: return [np.degrees(lon1), np.degrees(lon2)], [np.degrees(lat1), np.degrees(lat2)]
    t = np.linspace(0, 1, n)
    a, b = np.sin((1-t)*d)/np.sin(d), np.sin(t*d)/np.sin(d)
    x = a*np.cos(lat1)*np.cos(lon1) + b*np.cos(lat2)*np.cos(lon2)
    y = a*np.cos(lat1)*np.sin(lon1) + b*np.cos(lat2)*np.sin(lon2)
    z = a*np.sin(lat1) + b*np.sin(lat2)
    return np.degrees(np.arctan2(y, x)), np.degrees(np.arctan2(z, np.sqrt(x**2+y**2)))

def us_basemap(ax=None, figsize=(14, 9)):
    "Create a CONUS basemap"
    if ax is None: fig, ax = plt.subplots(1, 1, figsize=figsize)
    else: fig = ax.figure
    ax.set_facecolor(COLORS['bg']); fig.set_facecolor(COLORS['bg'])
    _draw_states(ax, load_states())
    ax.set_xlim(-125, -66); ax.set_ylim(24, 50)
    ax.set_aspect(1.3); ax.axis('off')
    return fig, ax

def plot_routes(ax, lines, color='#e74c3c', alpha=0.3, lw=1.0):
    "Plot ferry route arcs"
    for l in lines:
        lons, lats = _gc_pts(l['lat1'], l['lon1'], l['lat2'], l['lon2'])
        ax.plot(lons, lats, color=color, alpha=alpha, linewidth=lw, solid_capstyle='round')

def plot_airports(ax, volumes, color='#f1c40f', max_size=120):
    "Plot airport dots sized by trip volume"
    for v in volumes:
        ax.scatter(v['lon'], v['lat'], s=min(v['count']*3, max_size), color=color, alpha=0.8, zorder=5, edgecolors='none')

def savings_bar(ax, naive, nearest, optimized):
    "Horizontal comparison bar"
    ax.set_facecolor(COLORS['bg'])
    labels = ['Status Quo\n(Single Hub)', 'Nearest Base', 'Optimized\n(Multi-Base)']
    vals = [naive/1e6, nearest/1e6, optimized/1e6]
    colors = [COLORS['ferry_naive'], COLORS['accent'], COLORS['ferry_opt']]
    bars = ax.barh(labels, vals, color=colors, height=0.5, edgecolor='none')
    for bar, v in zip(bars, vals): ax.text(bar.get_width()+0.05, bar.get_y()+bar.get_height()/2, f'${v:.1f}M', va='center', ha='left', color='white', fontsize=12, fontweight='bold')
    ax.set_xlim(0, max(vals)*1.3)
    ax.tick_params(colors='white', labelsize=11)
    ax.spines[:].set_visible(False); ax.xaxis.set_visible(False)

def exec_summary(trips, sol_opt, apts, naive_single, naive_nearest, base='IND'):
    "Three-panel executive summary"
    from charternetwork.viz_data import route_lines_naive, route_lines_opt, airport_volumes
    fig = plt.figure(figsize=(20, 14)); fig.set_facecolor(COLORS['bg'])
    vols = airport_volumes(trips, apts)
    ax1 = fig.add_axes([0.02, 0.30, 0.47, 0.65])
    us_basemap(ax=ax1)
    plot_routes(ax1, route_lines_naive(trips, base, apts), color=COLORS['ferry_naive'], alpha=0.25, lw=1.0)
    plot_airports(ax1, vols)
    ax1.set_title(f'Status Quo: ${naive_single/1e6:.1f}M/mo', color='white', fontsize=16, fontweight='bold', pad=10)
    ax2 = fig.add_axes([0.51, 0.30, 0.47, 0.65])
    us_basemap(ax=ax2)
    plot_routes(ax2, route_lines_opt(sol_opt, trips, apts), color=COLORS['ferry_opt'], alpha=0.45, lw=1.4)
    plot_airports(ax2, vols)
    ax2.set_title(f'Optimized: ${sol_opt["ferry_cost"]/1e6:.1f}M/mo', color='white', fontsize=16, fontweight='bold', pad=10)
    ax3 = fig.add_axes([0.15, 0.03, 0.70, 0.22])
    savings_bar(ax3, naive_single, naive_nearest, sol_opt['ferry_cost'])
    savings = naive_single - sol_opt['ferry_cost']
    fig.suptitle(f'Charter Network Optimization: ${savings/1e6:.1f}M Monthly Savings ({(1-sol_opt["ferry_cost"]/naive_single)*100:.0f}%)', color='white', fontsize=20, fontweight='bold', y=0.98)
    return fig
