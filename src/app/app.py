"""
Seedr — Tennis Tournament Optimizer
====================================
Streamlit web app for data-driven tournament selection.

Usage:
    cd tennis-tournament-optimizer
    streamlit run src/app/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import time

# Add modeling directory to path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELING_DIR = os.path.join(APP_DIR, '..', 'modeling')
PROJECT_ROOT = os.path.join(APP_DIR, '..', '..')
sys.path.insert(0, MODELING_DIR)

from seasonal_optimizer import SeasonalOptimizer
from travel_costs import COUNTRY_CONTINENT
from points_to_rank import PointsRankMapper

# ==============================================================================
# PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="Seedr — Tournament Optimizer",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# CONSTANTS
# ==============================================================================

COUNTRY_NAMES = {
    'ARG': 'Argentina', 'AUS': 'Australia', 'AUT': 'Austria', 'BEL': 'Belgium',
    'BRA': 'Brazil', 'BUL': 'Bulgaria', 'CAN': 'Canada', 'CHI': 'Chile',
    'CHN': 'China', 'COL': 'Colombia', 'CRO': 'Croatia', 'CZE': 'Czech Republic',
    'DEN': 'Denmark', 'ECU': 'Ecuador', 'EGY': 'Egypt', 'ESP': 'Spain',
    'FIN': 'Finland', 'FRA': 'France', 'GBR': 'Great Britain', 'GEO': 'Georgia',
    'GER': 'Germany', 'GRE': 'Greece', 'HUN': 'Hungary', 'IND': 'India',
    'INA': 'Indonesia', 'ITA': 'Italy', 'JPN': 'Japan', 'KAZ': 'Kazakhstan',
    'KOR': 'South Korea', 'MAR': 'Morocco', 'MEX': 'Mexico', 'NED': 'Netherlands',
    'NOR': 'Norway', 'NZL': 'New Zealand', 'PER': 'Peru', 'POL': 'Poland',
    'POR': 'Portugal', 'ROU': 'Romania', 'RSA': 'South Africa', 'RUS': 'Russia',
    'SRB': 'Serbia', 'SLO': 'Slovenia', 'SVK': 'Slovakia', 'SUI': 'Switzerland',
    'SWE': 'Sweden', 'TUN': 'Tunisia', 'TUR': 'Turkey', 'UKR': 'Ukraine',
    'URU': 'Uruguay', 'USA': 'United States', 'UZB': 'Uzbekistan',
}
for code in COUNTRY_CONTINENT:
    if code not in COUNTRY_NAMES:
        COUNTRY_NAMES[code] = code

SURFACE_SEASONS = {
    'Australian Hard (Jan–Mar)': (1, 12),
    'Clay Season (Apr–Jun)': (14, 24),
    'Grass Season (Jun–Jul)': (24, 28),
    'US Hard (Jul–Sep)': (28, 39),
    'Fall Indoor (Oct–Nov)': (40, 47),
    'Custom range': None,
}

SURFACE_COLORS = {
    'Clay': '#D2691E',
    'Hard': '#4682B4',
    'Hard Indoor': '#7B68EE',
    'Grass': '#228B22',
    'Carpet': '#DAA520',
}

SURFACE_EMOJI = {
    'Clay': '🟤', 'Hard': '🔵', 'Hard Indoor': '🟣',
    'Grass': '🟢', 'Carpet': '🟠',
}

# Plotly color palette for schedules
SCHEDULE_COLORS = [
    '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B',
]

TEMPLATE_YEAR = 2025
N_SCHEDULES = 200
N_SIMS_TOURNAMENT = 400
N_SIMS_SCHEDULE = 2000


# ==============================================================================
# HELPERS
# ==============================================================================

def format_currency(val):
    if val >= 0:
        return f"${val:,.0f}"
    return f"-${abs(val):,.0f}"


def get_data_path():
    return os.path.join(PROJECT_ROOT, 'data', 'processed',
                        'atp_clean_both_ranked.csv')


@st.cache_resource(show_spinner="Loading optimizer engine...")
def load_optimizer(player_country):
    data_path = get_data_path()
    if not os.path.exists(data_path):
        return None
    optimizer = SeasonalOptimizer(player_country=player_country)
    optimizer.load_calendar(data_path, year=TEMPLATE_YEAR)
    return optimizer


def generate_schedule_name(sched, idx, tournament_evs, player_rank):
    """
    Generate a descriptive 2-3 word name for a schedule based on its
    characteristics: tier mix, surface, risk profile, density.
    """
    tournaments = sched.get('schedule', [])
    if not tournaments:
        return f"Schedule {idx + 1}"

    # --- Analyze tier mix ---
    categories = [t.get('category', '') for _, t in tournaments]
    has_atp = any('ATP' in c or 'Grand Slam' in c for c in categories)
    has_challenger = any('Challenger' in c for c in categories)
    has_itf = any(c.startswith('M15') or c.startswith('M25') for c in categories)

    challenger_pct = sum(1 for c in categories if 'Challenger' in c) / len(categories)
    atp_pct = sum(1 for c in categories if 'ATP' in c or 'Grand Slam' in c) / len(categories)

    if atp_pct >= 0.4:
        tier_word = "ATP Push"
    elif challenger_pct >= 0.6:
        tier_word = "Challenger Circuit"
    elif has_itf and not has_atp:
        tier_word = "ITF Grind"
    elif has_atp and has_challenger:
        tier_word = "Mixed Tier"
    else:
        tier_word = "Balanced"

    # --- Analyze surface ---
    surfaces = [t.get('surface', '') for _, t in tournaments]
    clay_pct = sum(1 for s in surfaces if 'Clay' in s) / len(surfaces)
    hard_pct = sum(1 for s in surfaces if 'Hard' in s) / len(surfaces)

    if clay_pct >= 0.8:
        surf_word = "Clay"
    elif hard_pct >= 0.8:
        surf_word = "Hard Court"
    elif clay_pct >= 0.5:
        surf_word = "Clay-Heavy"
    else:
        surf_word = "Mixed Surface"

    # --- Analyze risk/density ---
    n_tournaments = len(tournaments)
    weeks = [w for w, _ in tournaments]
    week_span = max(weeks) - min(weeks) + 1 if weeks else 1
    density = n_tournaments / week_span

    # Rank ambition: compare expected rank vs current
    exp_rank = sched.get('expected_final_rank', player_rank)
    rank_improvement = player_rank - exp_rank

    if density >= 0.7:
        style_word = "Packed"
    elif density <= 0.4:
        style_word = "Relaxed"
    elif rank_improvement > 30:
        style_word = "Aggressive"
    elif sched.get('net_prize', 0) > 0:
        style_word = "Profitable"
    else:
        style_word = "Steady"

    # --- Combine ---
    # Pick the most interesting two descriptors to avoid overly long names
    # Tier is always interesting; then pick between surface and style
    if surf_word in ('Clay', 'Hard Court', 'Mixed Surface'):
        return f"{style_word} {surf_word}"
    else:
        return f"{style_word} {tier_word}"


def create_distribution_chart(top_schedules, schedule_names, metric='points'):
    """
    Create a Plotly box plot comparing distributions across schedules.
    """
    if metric == 'points':
        raw_key = 'sim_points_raw'
        title = 'Ranking Points Distribution'
        y_label = 'Ranking Points'
        higher_better = True
    elif metric == 'prize':
        raw_key = 'sim_prizes_raw'
        title = 'Prize Money Distribution'
        y_label = 'Prize Money ($)'
        higher_better = True
    else:  # rank
        raw_key = 'sim_ranks_raw'
        title = 'Projected Ranking Distribution'
        y_label = 'ATP Ranking'
        higher_better = False

    fig = go.Figure()

    for i, (sched, name) in enumerate(zip(top_schedules, schedule_names)):
        raw = sched.get(raw_key, [])
        if not raw:
            continue

        color = SCHEDULE_COLORS[i % len(SCHEDULE_COLORS)]

        fig.add_trace(go.Box(
            y=raw,
            name=name,
            marker_color=color,
            boxmean=True,
            hoverinfo='y+name',
            line=dict(width=2),
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        yaxis_title=y_label,
        showlegend=False,
        height=380,
        margin=dict(l=60, r=20, t=50, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            gridcolor='rgba(128,128,128,0.2)',
            autorange='reversed' if not higher_better else True,
        ),
        font=dict(size=12),
    )

    return fig


def create_calendar_chart(sched, schedule_name, start_week, end_week):
    """
    Create a Plotly timeline showing tournaments on a week-by-week calendar.
    """
    tournaments = sched.get('schedule', [])
    if not tournaments:
        return None

    fig = go.Figure()

    # Background grid: all weeks in the window
    for w in range(start_week, end_week + 1):
        is_playing = any(week == w for week, _ in tournaments)
        fig.add_shape(
            type="rect",
            x0=w - 0.45, x1=w + 0.45,
            y0=0, y1=1,
            fillcolor='rgba(200,200,200,0.08)' if not is_playing else 'rgba(0,0,0,0)',
            line=dict(width=0),
            layer='below',
        )

    # Tournament blocks
    for i, (week, tournament) in enumerate(tournaments):
        name = tournament.get('tournament_name', '?')
        category = tournament.get('category', '?')
        surface = tournament.get('surface', '?')
        country = tournament.get('country', '?')
        country_name = COUNTRY_NAMES.get(country, country) if isinstance(country, str) else '?'

        color = SURFACE_COLORS.get(surface, '#888888')

        # Short display name: first word of tournament + country
        short_name = name.split()[0] if name != '?' else '?'
        if len(name.split()) > 1:
            short_name = ' '.join(name.split()[:2])
        if len(short_name) > 18:
            short_name = short_name[:16] + '..'

        fig.add_trace(go.Bar(
            x=[1],
            y=[week],
            orientation='h',
            marker=dict(
                color=color,
                line=dict(color='white', width=1),
            ),
            text=f"  {short_name}",
            textposition='inside',
            textfont=dict(color='white', size=11),
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"{category} | {SURFACE_EMOJI.get(surface, '')} {surface}<br>"
                f"{country_name}<br>"
                f"Week {week}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Rest week markers
    playing_weeks = {w for w, _ in tournaments}
    for w in range(start_week, end_week + 1):
        if w not in playing_weeks:
            fig.add_annotation(
                x=0.5, y=w,
                text="rest",
                showarrow=False,
                font=dict(size=9, color='rgba(150,150,150,0.6)'),
            )

    fig.update_layout(
        title=dict(text=f"📅 {schedule_name}", font=dict(size=14)),
        height=max(300, (end_week - start_week + 1) * 32 + 80),
        margin=dict(l=60, r=20, t=45, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, range=[0, 1.2]),
        yaxis=dict(
            title='Week',
            dtick=1,
            range=[end_week + 0.6, start_week - 0.6],
            gridcolor='rgba(128,128,128,0.15)',
        ),
        bargap=0.3,
        font=dict(size=12),
    )

    # Surface legend
    surfaces_used = list(set(
        t.get('surface', '?') for _, t in tournaments))
    for i, surf in enumerate(sorted(surfaces_used)):
        fig.add_trace(go.Bar(
            x=[0], y=[start_week - 10],  # off-screen
            marker_color=SURFACE_COLORS.get(surf, '#888'),
            name=surf,
            showlegend=True,
        ))

    fig.update_layout(
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.05,
            xanchor='center',
            x=0.5,
            font=dict(size=10),
        ),
    )

    return fig


# ==============================================================================
# SIDEBAR — INPUTS
# ==============================================================================

with st.sidebar:
    st.title("🎾 Seedr")
    st.caption("Tournament Optimizer")
    st.divider()

    st.markdown("**Tour:** ATP")
    st.caption("_WTA support coming soon_")
    st.divider()

    # --- Player profile ---
    st.subheader("Player Profile")

    player_rank = st.number_input(
        "Current ranking", min_value=1, max_value=2500,
        value=250, step=10,
        help="Your current ATP singles ranking")

    mapper = PointsRankMapper()
    estimated_points = mapper.rank_to_points(player_rank)

    player_points = st.number_input(
        "Current points", min_value=0, max_value=10000,
        value=max(0, int(estimated_points)),
        help="Auto-estimated from rank — adjust if you know your exact total")

    sorted_countries = sorted(COUNTRY_NAMES.items(), key=lambda x: x[1])
    country_labels = [f"{name} ({code})" for code, name in sorted_countries]
    country_codes = [code for code, _ in sorted_countries]
    default_idx = country_codes.index('FRA') if 'FRA' in country_codes else 0

    country_idx = st.selectbox(
        "Home country",
        range(len(country_labels)),
        format_func=lambda i: country_labels[i],
        index=default_idx,
        help="Used for travel cost and geographic scheduling")
    player_country = country_codes[country_idx]

    st.divider()

    # --- Planning window ---
    st.subheader("Planning Window")

    season_label = st.selectbox(
        "Surface season",
        list(SURFACE_SEASONS.keys()),
        index=1,
        help="Select a surface season or define a custom week range")

    season_range = SURFACE_SEASONS[season_label]
    if season_range is None:
        col1, col2 = st.columns(2)
        with col1:
            start_week = st.number_input("Start week", 1, 52, 14)
        with col2:
            end_week = st.number_input("End week", 1, 52, 24)
    else:
        start_week, end_week = season_range
        st.caption(f"Weeks {start_week}–{end_week}")

    st.caption(f"_Using {TEMPLATE_YEAR} calendar as template_")

    st.divider()

    # --- Preferences ---
    st.subheader("Preferences")

    surface_pref = st.selectbox(
        "Surface preference",
        ['Follow season', 'Clay only', 'Hard only', 'Grass only', 'No preference'],
        help="'Follow season' adapts to the time of year")
    surface_pref_map = {
        'Follow season': 'follow_season', 'Clay only': 'clay_only',
        'Hard only': 'hard_only', 'Grass only': 'grass_only',
        'No preference': 'no_preference',
    }

    travel_scope = st.selectbox(
        "Travel scope",
        ['Continental', 'National only', 'Global'],
        help="How far are you willing to travel?")
    travel_scope_map = {
        'Continental': 'continental', 'National only': 'national',
        'Global': 'global',
    }

    has_budget = st.toggle("Set a budget limit", value=False)
    if has_budget:
        max_budget = st.number_input(
            "Maximum season budget ($)", min_value=500, max_value=100000,
            value=8000, step=500,
            help="Total spend cap: travel + entry fees + accommodation")
    else:
        max_budget = None

    st.divider()

    run_clicked = st.button(
        "🚀 Optimize Schedule",
        use_container_width=True,
        type="primary")


# ==============================================================================
# MAIN AREA
# ==============================================================================

budget_str = f" | Budget {format_currency(max_budget)}" if max_budget else ""
st.title("🎾 Seedr — Tournament Schedule Optimizer")
st.markdown(
    f"**ATP** | Rank **{player_rank}** | "
    f"**{player_points}** pts | "
    f"{COUNTRY_NAMES.get(player_country, player_country)} | "
    f"{season_label}{budget_str}")

data_path = get_data_path()
if not os.path.exists(data_path):
    st.error(
        f"Processed data not found at `{data_path}`.\n\n"
        f"Run the pipeline first:\n\n"
        f"```\npython src/modeling/00_unified_pipeline.py\n```")
    st.stop()


# ==============================================================================
# RUN OPTIMIZER
# ==============================================================================

if run_clicked:
    with st.spinner("Loading optimizer and calendar data..."):
        optimizer = load_optimizer(player_country)

    if optimizer is None:
        st.error("Failed to load optimizer.")
        st.stop()

    if optimizer.player_country != player_country:
        st.cache_resource.clear()
        optimizer = load_optimizer(player_country)

    st.info(
        f"Generating and simulating {N_SCHEDULES} candidate schedules. "
        f"This typically takes 2–4 minutes...")

    progress_bar = st.progress(0, text="Initializing...")
    t_start = time.time()
    progress_bar.progress(10, text="Computing per-tournament expected values...")

    results = optimizer.optimize(
        player_rank=player_rank,
        player_points=player_points,
        planning_start_week=start_week,
        planning_end_week=end_week,
        n_schedules=N_SCHEDULES,
        n_sims_per_tournament=N_SIMS_TOURNAMENT,
        n_sims_per_schedule=N_SIMS_SCHEDULE,
        max_budget=max_budget,
        surface_preference=surface_pref_map[surface_pref],
        travel_scope=travel_scope_map[travel_scope],
        seed=42,
        verbose=False,
    )

    elapsed = time.time() - t_start
    progress_bar.progress(100, text=f"Done in {elapsed:.0f}s!")
    time.sleep(0.5)
    progress_bar.empty()

    st.session_state['results'] = results
    st.session_state['elapsed'] = elapsed
    st.session_state['start_week'] = start_week
    st.session_state['end_week'] = end_week


# ==============================================================================
# DISPLAY RESULTS
# ==============================================================================

if 'results' in st.session_state:
    results = st.session_state['results']
    elapsed = st.session_state.get('elapsed', 0)
    sw = st.session_state.get('start_week', 14)
    ew = st.session_state.get('end_week', 24)

    if 'error' in results:
        st.error(f"Optimization failed: {results['error']}")
        st.stop()

    meta = results['metadata']
    top_schedules = results['top_schedules']
    tournament_details = results.get('tournament_details', {})
    tournament_evs = results.get('tournament_evs', {})
    tournament_accept = results.get('tournament_accept', {})

    # --- Generate descriptive names for each schedule ---
    schedule_names = []
    for i, sched in enumerate(top_schedules):
        name = generate_schedule_name(sched, i, tournament_evs, meta['player_rank'])
        # Deduplicate: if name already used, append number
        if name in schedule_names:
            name = f"{name} ({i + 1})"
        schedule_names.append(name)

    # --- Summary ---
    st.success(
        f"Evaluated {meta['n_schedules_generated']} schedules across "
        f"{meta['n_eligible']} eligible tournaments in {elapsed:.0f}s.")

    with st.expander("ℹ️ How are schedules ranked?"):
        st.markdown("""
        Schedules are ranked by **expected ranking points** — the 
        probability-weighted average across thousands of Monte Carlo 
        simulations. Net financial return (prize minus costs) serves 
        as a tiebreaker.

        The top 5 are filtered for **diversity**: if two schedules 
        share more than 70% of the same tournaments, only the better 
        one is kept. Each schedule gets a descriptive name based on 
        its tier mix, surface focus, and strategic profile.

        All projections include ranking feedback (mid-season rank 
        changes affect later win probabilities) and week-by-week 
        points expiry from the previous year.
        """)

    # ==========================================================================
    # DISTRIBUTION COMPARISON (boxplots across all schedules)
    # ==========================================================================
    st.subheader("📊 Schedule Comparison")

    box_col1, box_col2 = st.columns(2)

    with box_col1:
        fig_pts = create_distribution_chart(
            top_schedules, schedule_names, metric='points')
        st.plotly_chart(fig_pts, use_container_width=True)

    with box_col2:
        fig_rank = create_distribution_chart(
            top_schedules, schedule_names, metric='rank')
        st.plotly_chart(fig_rank, use_container_width=True)

    # Prize money distribution below
    fig_prize = create_distribution_chart(
        top_schedules, schedule_names, metric='prize')
    st.plotly_chart(fig_prize, use_container_width=True)

    st.divider()

    # ==========================================================================
    # INDIVIDUAL SCHEDULE DETAILS
    # ==========================================================================
    st.subheader("📅 Schedule Details")

    if len(top_schedules) > 1:
        tabs = st.tabs(schedule_names)
    else:
        tabs = [st.container()]

    for idx, (tab, sched, sched_name) in enumerate(
            zip(tabs, top_schedules, schedule_names)):
        with tab:
            # --- Calendar view + metrics side by side ---
            cal_col, metrics_col = st.columns([3, 2])

            with cal_col:
                cal_fig = create_calendar_chart(sched, sched_name, sw, ew)
                if cal_fig:
                    st.plotly_chart(cal_fig, use_container_width=True)

            with metrics_col:
                # Key metrics
                rank_change = sched['expected_final_rank'] - meta['player_rank']

                st.metric("Expected Points", f"{sched['expected_points']:.0f}",
                           help=f"80% CI: [{sched['points_p10']:.0f}–{sched['points_p90']:.0f}]")
                st.metric("Expected Prize", format_currency(sched['expected_prize']))
                st.metric("Total Cost", format_currency(sched['total_cost']))
                st.metric("Net ROI", format_currency(sched['net_prize']),
                           delta=format_currency(sched['net_prize']),
                           delta_color="normal")
                st.metric("Projected Rank",
                           f"{sched['expected_final_rank']:.0f}",
                           delta=f"{rank_change:+.0f}",
                           delta_color="inverse")

            # --- Cost breakdown ---
            with st.expander("💰 Cost breakdown"):
                st.markdown(
                    f"- **Travel:** {format_currency(sched['travel_cost'])}\n"
                    f"- **Entry fees:** {format_currency(sched['entry_fees'])}\n"
                    f"- **Accommodation:** {format_currency(sched['accommodation_cost'])}\n"
                    f"- **Total:** {format_currency(sched['total_cost'])}")

            # --- Confidence intervals ---
            with st.expander("📈 Confidence intervals"):
                ci1, ci2 = st.columns(2)
                with ci1:
                    st.markdown("**Points distribution**")
                    st.markdown(
                        f"- Bad stretch (10th): **{sched['points_p10']:.0f}**\n"
                        f"- Conservative (20th): **{sched['points_p20']:.0f}**\n"
                        f"- Median: **{sched['points_p50']:.0f}**\n"
                        f"- Good stretch (80th): **{sched['points_p80']:.0f}**\n"
                        f"- Great stretch (90th): **{sched['points_p90']:.0f}**")
                with ci2:
                    st.markdown("**Rank projection**")
                    st.markdown(
                        f"- Best case (10th): **{sched['final_rank_p10']:.0f}**\n"
                        f"- Good (20th): **{sched['final_rank_p20']:.0f}**\n"
                        f"- Expected: **{sched['expected_final_rank']:.0f}**\n"
                        f"- Rough (80th): **{sched['final_rank_p80']:.0f}**\n"
                        f"- Worst case (90th): **{sched['final_rank_p90']:.0f}**")

            # --- Tournament table ---
            with st.expander("📋 Tournament details"):
                rows = []
                for week, tournament in sched['schedule']:
                    name = tournament.get('tournament_name', '?')
                    category = tournament.get('category', '?')
                    surface = tournament.get('surface', '?')
                    country = tournament.get('country', '?')
                    ev = tournament_evs.get(name, 0)
                    accept = tournament_accept.get(name, 1.0)
                    details = tournament_details.get(name, {})

                    rows.append({
                        'Wk': week,
                        'Tournament': name,
                        'Category': category,
                        'Surface': f"{SURFACE_EMOJI.get(surface, '⚪')} {surface}",
                        'Country': (COUNTRY_NAMES.get(country, country)
                                    if isinstance(country, str) else '?'),
                        'EV': f"{ev:.1f}",
                        'Prize': format_currency(
                            details.get('expected_prize', 0)),
                        'Accept': f"{accept:.0%}",
                    })

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True)

            # --- Round probabilities ---
            with st.expander("🎯 Round-by-round probabilities"):
                for week, tournament in sched['schedule']:
                    name = tournament.get('tournament_name', '?')
                    details = tournament_details.get(name, {})
                    rp = details.get('round_probs', {})
                    if rp:
                        prob_str = " → ".join(
                            f"**{r}** {p:.0%}" for r, p in rp.items())
                        st.markdown(f"**{name}:** {prob_str}")

    st.divider()

    # --- All eligible tournaments ---
    with st.expander("📊 All eligible tournaments ranked by expected value"):
        all_rows = []
        for name, ev in sorted(tournament_evs.items(), key=lambda x: -x[1]):
            details = tournament_details.get(name, {})
            accept = tournament_accept.get(name, 1.0)
            raw_ev = results.get('tournament_raw_evs', {}).get(name, ev)
            all_rows.append({
                'Tournament': name,
                'Effective EV': f"{ev:.1f}",
                'Raw EV': f"{raw_ev:.1f}",
                'Acceptance': f"{accept:.0%}",
                'Exp. Prize': format_currency(
                    details.get('expected_prize', 0)),
            })
        st.dataframe(pd.DataFrame(all_rows),
                      use_container_width=True, hide_index=True)

else:
    # =========================================================================
    # WELCOME SCREEN
    # =========================================================================
    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("""
        ### How it works

        1. **Set your profile** — Enter your ranking, points, and home 
           country in the sidebar
        2. **Choose a planning window** — Pick a surface season or custom 
           week range
        3. **Set preferences** — Surface, travel scope, optional budget cap
        4. **Hit Optimize** — Seedr generates hundreds of candidate 
           schedules and simulates each one thousands of times using Monte 
           Carlo methods
        5. **Compare options** — Review the top diverse schedules with 
           distribution charts, calendar views, and financial projections

        ### How schedules are ranked

        Schedules are ranked by **expected ranking points** — the single 
        highest-leverage metric for a developing player. Net financial 
        return is used as a tiebreaker. The top results are filtered for 
        diversity so you see genuinely different strategic options, each 
        with a descriptive name reflecting its character.
        """)

    with col_right:
        st.markdown("""
        ### Quick start profiles

        **Rank ~250 clay specialist**
        - Clay Season, Follow season
        - Travel: Continental

        **Rank ~500 developing player**
        - Any season, No preference
        - Budget: $5,000

        **Rank ~100 Slam qualifier**
        - Clay Season, Follow season
        - Travel: Global
        """)

        st.markdown("---")
        st.markdown("""
        ### Current limitations

        - **ATP only** — WTA model not yet 
          validated
        - **Calendar template** — Uses the 2025 
          schedule; 2026 dates may differ slightly
        - **No injury/fatigue modeling** — rest 
          weeks are rule-based, not adaptive
        """)

    st.info(
        "👈 Configure your profile in the sidebar and click "
        "**Optimize Schedule** to get started.")
