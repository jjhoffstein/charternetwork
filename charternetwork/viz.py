import json, numpy as np, matplotlib.pyplot as plt
from pathlib import Path

COLORS = dict(ferry_naive='#e74c3c', ferry_opt='#27ae60', accent='#2980b9',
              bg='#ffffff', ocean='#a8c8e8', land='#f5f5f2', border='#9ea8b3',
              text='#212529', airport='#e67e22')
SKIP_STATES = {'Alaska', 'Hawaii', 'Puerto Rico'}


def load_states():
    with open(Path(__file__).parent.parent / 'data/geo/us_states.json') as f:
        return json.load(f)


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
    for v in volumes:
        ax.scatter(v['lon'], v['lat'], s=min(v['count']*3, max_size), color=color,
                   alpha=0.7, zorder=5, edgecolors='white', linewidths=0.3)


def plot_bases(ax, bases, apts, color='#2c3e50', marker='*', size=200):
    for b in bases:
        ax.scatter(apts.loc[b].longitude_deg, apts.loc[b].latitude_deg, s=size,
                   color=color, marker=marker, zorder=10, edgecolors='white', linewidths=0.5)


def savings_bar(ax, single, nearest, optimized):
    ax.set_facecolor(COLORS['bg'])
    labels = ['Optimized\n(Multi-Base)', 'Nearest Base', 'Single Hub']
    vals = [optimized/1e6, nearest/1e6, single/1e6]
    colors = [COLORS['ferry_opt'], COLORS['accent'], COLORS['ferry_naive']]
    bars = ax.barh(labels, vals, color=colors, height=0.5, edgecolor='none')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width()+0.05, bar.get_y()+bar.get_height()/2, f'${v:.1f}M',
                va='center', ha='left', color=COLORS['text'], fontsize=11, fontweight='bold')
    ax.set_xlim(0, max(vals)*1.3)
    ax.tick_params(colors=COLORS['text'], labelsize=10)
    ax.spines[:].set_visible(False); ax.xaxis.set_visible(False)


# ---------------------------------------------------------------------------
# V.1: Reusable single-panel helper
# ---------------------------------------------------------------------------

def _single_panel(ax, lines, vols, bases, apts, title, color, route_alpha=0.3, route_lw=1.0):
    "Draw a single strategy panel on the given axes."
    us_basemap(ax=ax)
    plot_routes(ax, lines, color=color, alpha=route_alpha, lw=route_lw)
    plot_airports(ax, vols)
    plot_bases(ax, bases, apts)
    ax.set_title(title, color=color, fontsize=14, fontweight='bold', pad=8)


# ---------------------------------------------------------------------------
# V.2: Standalone panel renderer
# ---------------------------------------------------------------------------

def render_panel(trips, apts, lines, bases, cost, label, color, figsize=(14, 9)):
    "Render a single strategy as a standalone figure with cost callout."
    from charternetwork.viz_data import airport_volumes
    vols = airport_volumes(trips, apts)
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.set_facecolor(COLORS['bg'])
    _single_panel(ax, lines, vols, bases, apts,
                  title=f'{label}: ${cost/1e6:.1f}M/mo ferry cost',
                  color=color, route_alpha=0.4, route_lw=1.2)
    # Prominent cost callout
    ax.text(0.98, 0.02, f'${cost/1e6:.1f}M/mo', transform=ax.transAxes,
            fontsize=28, fontweight='bold', color=color,
            ha='right', va='bottom', alpha=0.8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))
    return fig


# ---------------------------------------------------------------------------
# V.3: Chain detail map
# ---------------------------------------------------------------------------

def render_chain_detail(chain, apts, figsize=(12, 8)):
    "Render a zoomed regional map of a single trip chain."
    trips = chain['trips']
    if not trips: return None

    # Collect all airports in the chain
    codes = set()
    for t in trips:
        codes.add(t.home_apt)
        codes.add(t.game_apt)
    pts = [(apts.loc[c].longitude_deg, apts.loc[c].latitude_deg, c) for c in codes if c in apts.index]
    if not pts: return None

    lons, lats, labels = zip(*pts)
    pad = 3.0
    lon_min, lon_max = min(lons) - pad, max(lons) + pad
    lat_min, lat_max = min(lats) - pad/1.3, max(lats) + pad/1.3

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.set_facecolor(COLORS['bg'])
    ax.set_facecolor(COLORS['ocean'])
    _draw_states(ax, load_states())
    ax.set_xlim(lon_min, lon_max); ax.set_ylim(lat_min, lat_max)
    ax.set_aspect(1.3); ax.axis('off')

    # Draw revenue legs (outbound + return) as thin solid lines
    for t in trips:
        if t.home_apt in apts.index and t.game_apt in apts.index:
            h = apts.loc[t.home_apt]
            g = apts.loc[t.game_apt]
            lns, lts = _gc_pts(h.latitude_deg, h.longitude_deg, g.latitude_deg, g.longitude_deg)
            ax.plot(lns, lts, color=COLORS['accent'], alpha=0.5, linewidth=1.5,
                    linestyle='-', solid_capstyle='round')

    # Draw ferry legs as dashed lines with cost annotations
    for i in range(len(trips) - 1):
        ta, tb = trips[i], trips[i+1]
        if ta.home_apt in apts.index and tb.home_apt in apts.index:
            ha = apts.loc[ta.home_apt]
            hb = apts.loc[tb.home_apt]
            lns, lts = _gc_pts(ha.latitude_deg, ha.longitude_deg, hb.latitude_deg, hb.longitude_deg)
            ax.plot(lns, lts, color=COLORS['ferry_opt'], alpha=0.8, linewidth=2.5,
                    linestyle='--', solid_capstyle='round')
            # Cost annotation at midpoint
            mid_idx = len(lns) // 2
            from charternetwork.ingest import leg_dist
            f_nm = leg_dist(ta.home_apt, tb.home_apt, apts) if ta.home_apt != tb.home_apt else 0
            ax.annotate(f'{f_nm:.0f}nm', xy=(lns[mid_idx], lts[mid_idx]),
                        fontsize=9, fontweight='bold', color=COLORS['ferry_opt'],
                        ha='center', va='bottom',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

    # Plot and label airports
    for lon, lat, code in pts:
        ax.scatter(lon, lat, s=100, color=COLORS['airport'], zorder=10,
                   edgecolors='white', linewidths=0.8)
        # Find team name for this airport
        team_label = code
        for t in trips:
            if t.home_apt == code: team_label = f'{code} ({t.team})'; break
            if t.game_apt == code: team_label = f'{code} (game)'; break
        ax.annotate(team_label, xy=(lon, lat), xytext=(5, 5),
                    textcoords='offset points', fontsize=8, fontweight='bold',
                    color=COLORS['text'],
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

    # Title and legend
    n = chain['n_hops'] + 1
    label = 'Triangle' if n == 3 else 'Daisy-Chain' if n >= 4 else 'Pair'
    ax.set_title(f'{label} Route: {n} trips chained on {chain["tail"]}\n'
                 f'Ferry cost: ${chain["ferry_cost"]:,.0f}',
                 fontsize=14, fontweight='bold', color=COLORS['text'], pad=12)

    # Legend
    from matplotlib.lines import Line2D
    legend_els = [
        Line2D([0],[0], color=COLORS['accent'], lw=1.5, label='Revenue legs'),
        Line2D([0],[0], color=COLORS['ferry_opt'], lw=2.5, ls='--', label='Ferry legs'),
    ]
    ax.legend(handles=legend_els, loc='lower left', fontsize=10, framealpha=0.9)

    return fig


# ---------------------------------------------------------------------------
# Refactored exec_summary using _single_panel
# ---------------------------------------------------------------------------

def exec_summary(trips, sol_opt, apts, single_hub, nearest_base, base='IND', bases=None):
    from charternetwork.viz_data import route_lines_naive, route_lines_nearest, route_lines_opt, airport_volumes
    if bases is None: bases = [base]
    fig = plt.figure(figsize=(22, 14)); fig.set_facecolor(COLORS['bg'])
    vols = airport_volumes(trips, apts)
    w, h, y0 = 0.31, 0.55, 0.38

    ax1 = fig.add_axes([0.01, y0, w, h])
    _single_panel(ax1, route_lines_naive(trips, base, apts), vols, [base], apts,
                  title=f'Single Hub: ${single_hub/1e6:.1f}M/mo',
                  color=COLORS['ferry_naive'])

    ax2 = fig.add_axes([0.34, y0, w, h])
    _single_panel(ax2, route_lines_nearest(trips, bases, apts), vols, bases, apts,
                  title=f'Nearest Base: ${nearest_base/1e6:.1f}M/mo',
                  color=COLORS['accent'], route_alpha=0.35)

    ax3 = fig.add_axes([0.67, y0, w, h])
    _single_panel(ax3, route_lines_opt(sol_opt, trips, apts), vols, bases, apts,
                  title=f'Optimized: ${sol_opt["ferry_cost"]/1e6:.1f}M/mo',
                  color=COLORS['ferry_opt'], route_alpha=0.5, route_lw=1.4)

    ax4 = fig.add_axes([0.15, 0.04, 0.70, 0.25])
    savings_bar(ax4, single_hub, nearest_base, sol_opt['ferry_cost'])

    savings = single_hub - sol_opt['ferry_cost']
    fig.suptitle(f'Charter Network Optimization: ${savings/1e6:.1f}M Monthly Savings '
                 f'({(1-sol_opt["ferry_cost"]/single_hub)*100:.0f}%) vs Single Hub',
                 color=COLORS['text'], fontsize=20, fontweight='bold', y=0.98)
    return fig
