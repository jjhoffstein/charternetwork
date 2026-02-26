import json, numpy as np, matplotlib.pyplot as plt
from pathlib import Path

COLORS = dict(ferry_naive='#e74c3c', ferry_opt='#27ae60', accent='#2980b9', bg='#ffffff', ocean='#a8c8e8', land='#f5f5f2', border='#9ea8b3', text='#212529', airport='#e67e22')
SKIP_STATES = {'Alaska', 'Hawaii', 'Puerto Rico'}

def load_states():
    with open(Path(__file__).parent.parent / 'data/geo/us_states.json') as f: return json.load(f)

def _draw_states(ax, states):
    for feat in states['features']:
        if feat['properties']['name'] in SKIP_STATES: continue
        geom = feat['geometry']
        polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            for ring in poly:
                xs, ys = zip(*ring)
                ax.fill(xs, ys, facecolor=COLORS['land'], edgecolor=COLORS['border'], linewidth=0.5)

def _gc_pts(lat1, lon1, lat2, lon2, n=50):
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
    if ax is None: fig, ax = plt.subplots(1, 1, figsize=figsize)
    else: fig = ax.figure
    ax.set_facecolor(COLORS['ocean']); fig.set_facecolor(COLORS['bg'])
    _draw_states(ax, load_states())
    ax.set_xlim(-125, -66); ax.set_ylim(24, 50)
    ax.set_aspect(1.3); ax.axis('off')
    return fig, ax

def plot_routes(ax, lines, color='#e74c3c', alpha=0.3, lw=1.0):
    for l in lines:
        lons, lats = _gc_pts(l['lat1'], l['lon1'], l['lat2'], l['lon2'])
        ax.plot(lons, lats, color=color, alpha=alpha, linewidth=lw, solid_capstyle='round')

def plot_airports(ax, volumes, color=None, max_size=120):
    if color is None: color = COLORS['airport']
    for v in volumes: ax.scatter(v['lon'], v['lat'], s=min(v['count']*3, max_size), color=color, alpha=0.7, zorder=5, edgecolors='white', linewidths=0.3)

def plot_bases(ax, bases, apts, color='#2c3e50', marker='*', size=200):
    for b in bases: ax.scatter(apts.loc[b].longitude_deg, apts.loc[b].latitude_deg, s=size, color=color, marker=marker, zorder=10, edgecolors='white', linewidths=0.5)

def savings_bar(ax, single, nearest, optimized):
    ax.set_facecolor(COLORS['bg'])
    labels = ['Optimized\n(Multi-Base)', 'Nearest Base', 'Single Hub']
    vals = [optimized/1e6, nearest/1e6, single/1e6]
    colors = [COLORS['ferry_opt'], COLORS['accent'], COLORS['ferry_naive']]
    bars = ax.barh(labels, vals, color=colors, height=0.5, edgecolor='none')
    for bar, v in zip(bars, vals): ax.text(bar.get_width()+0.05, bar.get_y()+bar.get_height()/2, f'${v:.1f}M', va='center', ha='left', color=COLORS['text'], fontsize=11, fontweight='bold')
    ax.set_xlim(0, max(vals)*1.3)
    ax.tick_params(colors=COLORS['text'], labelsize=10)
    ax.spines[:].set_visible(False); ax.xaxis.set_visible(False)

def exec_summary(trips, sol_opt, apts, single_hub, nearest_base, base='IND', bases=None):
    from charternetwork.viz_data import route_lines_naive, route_lines_nearest, route_lines_opt, airport_volumes
    if bases is None: bases = [base]
    fig = plt.figure(figsize=(22, 14)); fig.set_facecolor(COLORS['bg'])
    vols = airport_volumes(trips, apts)
    w, h, y0 = 0.31, 0.55, 0.38
    ax1 = fig.add_axes([0.01, y0, w, h])
    us_basemap(ax=ax1)
    plot_routes(ax1, route_lines_naive(trips, base, apts), color=COLORS['ferry_naive'], alpha=0.3, lw=1.0)
    plot_airports(ax1, vols); plot_bases(ax1, [base], apts, size=250)
    ax1.set_title(f'Single Hub: ${single_hub/1e6:.1f}M/mo', color=COLORS['ferry_naive'], fontsize=14, fontweight='bold', pad=8)
    ax2 = fig.add_axes([0.34, y0, w, h])
    us_basemap(ax=ax2)
    plot_routes(ax2, route_lines_nearest(trips, bases, apts), color=COLORS['accent'], alpha=0.35, lw=1.0)
    plot_airports(ax2, vols); plot_bases(ax2, bases, apts)
    ax2.set_title(f'Nearest Base: ${nearest_base/1e6:.1f}M/mo', color=COLORS['accent'], fontsize=14, fontweight='bold', pad=8)
    ax3 = fig.add_axes([0.67, y0, w, h])
    us_basemap(ax=ax3)
    plot_routes(ax3, route_lines_opt(sol_opt, trips, apts), color=COLORS['ferry_opt'], alpha=0.5, lw=1.4)
    plot_airports(ax3, vols); plot_bases(ax3, bases, apts)
    ax3.set_title(f'Optimized: ${sol_opt["ferry_cost"]/1e6:.1f}M/mo', color=COLORS['ferry_opt'], fontsize=14, fontweight='bold', pad=8)
    ax4 = fig.add_axes([0.15, 0.04, 0.70, 0.25])
    savings_bar(ax4, single_hub, nearest_base, sol_opt['ferry_cost'])
    savings = single_hub - sol_opt['ferry_cost']
    fig.suptitle(f'Charter Network Optimization: ${savings/1e6:.1f}M Monthly Savings ({(1-sol_opt["ferry_cost"]/single_hub)*100:.0f}%) vs Single Hub', color=COLORS['text'], fontsize=20, fontweight='bold', y=0.98)
    return fig
