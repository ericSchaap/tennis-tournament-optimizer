"""
Tennis Tournament Optimizer - Tournament Economics
===================================================

Ranking points and prize money tables per tournament category and round.

Sources:
- ATP Rulebook 2025/2026 (ranking points)
- ITF/ATP points PDF (uploaded by user)
- ATP Tour website (prize money structures)

Round naming convention in our data:
  '1/128', '1/64', '1/32', '1/16', '1/8', 'QF', 'SF', 'F'
  (plus 'W' for winner, computed as winning the Final)
"""

# ==============================================================================
# ATP RANKING POINTS
# ==============================================================================
# Key: category pattern -> {round: points}
# Rounds use Coretennis naming: 1/64, 1/32, 1/16, 1/8, QF, SF, F, W
# "W" = winning the final (not a separate round in data, but needed for payoff)

ATP_RANKING_POINTS = {
    # Grand Slams (128 draw)
    "Grand Slam": {
        "1/128": 10, "1/64": 45, "1/32": 90, "1/16": 180,
        "1/8": 360, "QF": 720, "SF": 1200, "F": 2000,
        # Qualifying
        "Q1": 0, "Q2": 8, "Q3": 16, "QF_Q": 25,
    },

    # ATP Masters 1000 - 96 draw
    "ATP 1000 (96)": {
        "1/64": 10, "1/32": 25, "1/16": 45, "1/8": 90,
        "QF": 180, "SF": 360, "F": 600, "W": 1000,
        "Q1": 0, "Q2": 8, "Q3": 16,
    },

    # ATP Masters 1000 - 48/56 draw
    "ATP 1000 (48)": {
        "1/32": 10, "1/16": 45, "1/8": 90,
        "QF": 180, "SF": 360, "F": 600, "W": 1000,
        "Q1": 0, "Q2": 16, "Q3": 25,
    },

    # ATP 500 - 48 draw
    "ATP 500 (48)": {
        "1/32": 20, "1/16": 45, "1/8": 90,
        "QF": 180, "SF": 300, "F": 500,
        "Q1": 0, "Q2": 4, "Q3": 10,
    },

    # ATP 500 - 32 draw
    "ATP 500 (32)": {
        "1/16": 45, "1/8": 90,
        "QF": 180, "SF": 300, "F": 500,
        "Q1": 0, "Q2": 10, "Q3": 20,
    },

    # ATP 250 - 48 draw
    "ATP 250 (48)": {
        "1/32": 5, "1/16": 10, "1/8": 20,
        "QF": 45, "SF": 90, "F": 150, "W": 250,
        "Q1": 0, "Q2": 3,
    },

    # ATP 250 - 32 draw
    "ATP 250 (32)": {
        "1/16": 20, "1/8": 45,
        "QF": 90, "SF": 150, "F": 250,
        "Q1": 0, "Q2": 6, "Q3": 12,
    },

    # Challenger 125
    "Challenger 125": {
        "1/16": 5, "1/8": 10,
        "QF": 25, "SF": 45, "F": 75, "W": 125,
    },

    # Challenger 110
    "Challenger 110": {
        "1/16": 5, "1/8": 9,
        "QF": 20, "SF": 40, "F": 65, "W": 110,
    },

    # Challenger 100
    "Challenger 100": {
        "1/16": 5, "1/8": 8,
        "QF": 18, "SF": 35, "F": 60, "W": 100,
    },

    # Challenger 90
    "Challenger 90": {
        "1/16": 5, "1/8": 8,
        "QF": 17, "SF": 33, "F": 55, "W": 90,
    },

    # Challenger 80
    "Challenger 80": {
        "1/16": 3, "1/8": 7,
        "QF": 15, "SF": 29, "F": 48, "W": 80,
    },

    # Challenger 50 (generic/old format)
    "Challenger 50": {
        "1/16": 3, "1/8": 6,
        "QF": 12, "SF": 25, "F": 40, "W": 65,
    },

    # ITF M25+H (from 5 August 2019 onwards)
    "M25+H": {
        "1/16": 1, "1/8": 3,
        "QF": 6, "SF": 12, "F": 20,
    },

    # ITF M25
    "M25": {
        "1/16": 1, "1/8": 3,
        "QF": 6, "SF": 12, "F": 20,
    },

    # ITF M15+H
    "M15+H": {
        "1/8": 1, "1/16": 1,
        "QF": 2, "SF": 4, "F": 6, "W": 10,
    },

    # ITF M15
    "M15": {
        "1/8": 1, "1/16": 1,
        "QF": 2, "SF": 4, "F": 6, "W": 10,
    },
}

# Map Coretennis categories to points table keys
# (handles draw size variants)
def get_points_table(category, draw_size=None):
    """Get the ranking points table for a tournament category."""
    cat = category.strip()

    if "Grand Slam" in cat:
        return ATP_RANKING_POINTS["Grand Slam"]

    if cat == "ATP 1000":
        if draw_size and draw_size >= 96:
            return ATP_RANKING_POINTS["ATP 1000 (96)"]
        return ATP_RANKING_POINTS["ATP 1000 (48)"]

    if cat == "ATP 500":
        if draw_size and draw_size >= 48:
            return ATP_RANKING_POINTS["ATP 500 (48)"]
        return ATP_RANKING_POINTS["ATP 500 (32)"]

    if cat == "ATP 250":
        if draw_size and draw_size >= 48:
            return ATP_RANKING_POINTS["ATP 250 (48)"]
        return ATP_RANKING_POINTS["ATP 250 (32)"]

    if "Challenger" in cat:
        # Extract prize level from category name
        for level in ["175", "125", "110", "100", "90", "80", "75", "50"]:
            if level in cat:
                # Map to closest defined table
                if int(level) >= 125:
                    return ATP_RANKING_POINTS["Challenger 125"]
                elif int(level) >= 100:
                    return ATP_RANKING_POINTS["Challenger 100"]
                elif int(level) >= 80:
                    return ATP_RANKING_POINTS["Challenger 80"]
                else:
                    return ATP_RANKING_POINTS["Challenger 50"]
        # Default Challengers
        return ATP_RANKING_POINTS["Challenger 80"]

    if cat == "M25":
        return ATP_RANKING_POINTS["M25"]

    if cat == "M15":
        return ATP_RANKING_POINTS["M15"]

    return None


# ==============================================================================
# ATP PRIZE MONEY (approximate, in USD)
# ==============================================================================
# These are approximate typical prize money distributions.
# Actual amounts vary by tournament. These are used for expected value estimates.

ATP_PRIZE_MONEY = {
    "Grand Slam": {
        "1/128": 50000, "1/64": 100000, "1/32": 165000, "1/16": 275000,
        "1/8": 450000, "QF": 750000, "SF": 1300000, "F": 2200000, "W": 3600000,
    },

    "ATP 1000": {
        "1/64": 8000, "1/32": 16000, "1/16": 32000, "1/8": 60000,
        "QF": 115000, "SF": 215000, "F": 400000, "W": 750000,
    },

    "ATP 500": {
        "1/32": 6000, "1/16": 12000, "1/8": 25000,
        "QF": 50000, "SF": 95000, "F": 170000, "W": 300000,
    },

    "ATP 250": {
        "1/32": 3000, "1/16": 6500, "1/8": 13000,
        "QF": 25000, "SF": 45000, "F": 85000, "W": 150000,
    },

    # Challenger prize money varies with category level
    "Challenger 175": {
        "1/16": 1800, "1/8": 3600,
        "QF": 7200, "SF": 14000, "F": 25000, "W": 43000,
    },

    "Challenger 125": {
        "1/16": 1200, "1/8": 2400,
        "QF": 4800, "SF": 9600, "F": 16500, "W": 28500,
    },

    "Challenger 100": {
        "1/16": 1000, "1/8": 2000,
        "QF": 3800, "SF": 7500, "F": 13000, "W": 22500,
    },

    "Challenger 80": {
        "1/16": 700, "1/8": 1400,
        "QF": 2800, "SF": 5500, "F": 9500, "W": 16500,
    },

    "Challenger 50": {
        "1/16": 480, "1/8": 960,
        "QF": 2280, "SF": 4440, "F": 7680, "W": 14400,
    },

    # ITF
    "M25": {
        "1/16": 200, "1/8": 400,
        "QF": 900, "SF": 1800, "F": 3500, "W": 6000,
    },

    "M15": {
        "1/16": 100, "1/8": 200,
        "QF": 500, "SF": 1000, "F": 2000, "W": 3500,
    },
}


def get_prize_table(category):
    """Get approximate prize money table for a tournament category."""
    cat = category.strip()

    if "Grand Slam" in cat:
        return ATP_PRIZE_MONEY["Grand Slam"]
    if cat == "ATP 1000":
        return ATP_PRIZE_MONEY["ATP 1000"]
    if cat == "ATP 500":
        return ATP_PRIZE_MONEY["ATP 500"]
    if cat in ("ATP 250", "ATP Finals"):
        return ATP_PRIZE_MONEY["ATP 250"]

    if "Challenger" in cat:
        for level in ["175", "125", "110", "100", "90", "80", "75", "50"]:
            if level in cat:
                if int(level) >= 125:
                    return ATP_PRIZE_MONEY["Challenger 125"]
                elif int(level) >= 100:
                    return ATP_PRIZE_MONEY["Challenger 100"]
                elif int(level) >= 75:
                    return ATP_PRIZE_MONEY["Challenger 80"]
                else:
                    return ATP_PRIZE_MONEY["Challenger 50"]
        return ATP_PRIZE_MONEY["Challenger 80"]

    if cat == "M25":
        return ATP_PRIZE_MONEY["M25"]
    if cat == "M15":
        return ATP_PRIZE_MONEY["M15"]

    return None


# ==============================================================================
# TOURNAMENT CALENDAR (extracted from historical data)
# ==============================================================================

def extract_calendar(clean_data_path, year=2025):
    """
    Extract tournament calendar from clean match data.

    Returns DataFrame with one row per tournament:
    tournament_name, category, surface, location, country, start_date, end_date,
    tier, tier_name, level, mandatory, n_matches, draw_size_est
    """
    import pandas as pd

    cols = ['tournament_name', 'category', 'surface', 'location', 'country',
            'start_date', 'end_date', 'year', 'tier', 'tier_name', 'level',
            'mandatory', 'round', 'player_rank']

    df = pd.read_csv(clean_data_path, usecols=cols, low_memory=False)
    df = df[df['year'] == year]

    # One row per tournament
    cal = df.groupby(['tournament_name', 'category', 'surface',
                       'location', 'country']).agg(
        start_date=('start_date', 'first'),
        end_date=('end_date', 'first'),
        tier=('tier', 'first'),
        tier_name=('tier_name', 'first'),
        level=('level', 'first'),
        mandatory=('mandatory', 'first'),
        n_matches=('round', 'count'),
        n_rounds=('round', 'nunique'),
        rounds=('round', lambda x: sorted(x.unique())),
        median_player_rank=('player_rank', 'median'),
    ).reset_index()

    # Estimate draw size from round structure
    def estimate_draw(rounds, n_matches):
        if '1/64' in rounds:
            return 128
        elif '1/32' in rounds:
            return 64
        elif '1/16' in rounds:
            return 32
        else:
            return 16

    cal['draw_size_est'] = cal.apply(
        lambda r: estimate_draw(r['rounds'], r['n_matches']), axis=1)

    # Add points and prize tables
    cal['points_table'] = cal['category'].apply(
        lambda c: get_points_table(c) is not None)
    cal['prize_table'] = cal['category'].apply(
        lambda c: get_prize_table(c) is not None)

    return cal.sort_values('start_date').reset_index(drop=True)


# ==============================================================================
# EXPECTED VALUE CALCULATOR
# ==============================================================================

def tournament_expected_value(player_rank, category, surface, tier_group,
                               median_field_rank=None, draw_size=32,
                               entry_cost=0, n_sims=10000, seed=None):
    """
    Calculate expected ranking points, prize money, and ROI for a tournament.

    Args:
        player_rank: Player's current ranking
        category: Tournament category (e.g., 'Challenger 100', 'ATP 250')
        surface: Court surface
        tier_group: Tier group for win probability model
        median_field_rank: Median ranking of players in the draw
        draw_size: Number of players in main draw
        entry_cost: Total cost (entry fee + travel + accommodation)
        n_sims: Monte Carlo simulations
        seed: Random seed

    Returns:
        dict with expected prize, points, ROI, round probabilities
    """
    import random
    import numpy as np

    # Import win probability model
    from win_probability import WinProbabilityModel
    model = WinProbabilityModel()

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Generate plausible draw
    if median_field_rank is None:
        median_field_rank = player_rank  # assume similar level field

    # Log-normal draw around median
    draw = np.random.lognormal(
        mean=np.log(median_field_rank),
        sigma=0.6,
        size=draw_size
    ).astype(int)
    draw = np.clip(draw, 1, 3000).tolist()

    # Get points and prize tables
    points_table = get_points_table(category) or {}
    prize_table = get_prize_table(category) or {}

    # Determine round sequence based on draw size
    if draw_size >= 128:
        rounds = ['1/64', '1/32', '1/16', '1/8', 'QF', 'SF', 'F', 'W']
    elif draw_size >= 64:
        rounds = ['1/32', '1/16', '1/8', 'QF', 'SF', 'F', 'W']
    elif draw_size >= 32:
        rounds = ['1/16', '1/8', 'QF', 'SF', 'F', 'W']
    else:
        rounds = ['1/8', 'QF', 'SF', 'F', 'W']

    # Simulate
    round_counts = {r: 0 for r in rounds}
    round_counts[rounds[0]] = n_sims

    for _ in range(n_sims):
        for r_idx in range(1, len(rounds)):
            opp_rank = random.choice(draw)
            p_win = model.predict(player_rank, opp_rank, surface, tier_group)
            if random.random() < p_win:
                round_counts[rounds[r_idx]] += 1
            else:
                break

    round_probs = {r: c / n_sims for r, c in round_counts.items()}

    # Calculate expected values
    exp_prize = 0.0
    exp_points = 0.0

    for i, r in enumerate(rounds):
        p_reach = round_probs[r]
        p_next = round_probs[rounds[i + 1]] if i + 1 < len(rounds) else 0.0
        p_exit = p_reach - p_next

        # For "W" (winner), use "F" key in points/prize if "W" not present
        pts_key = r if r in points_table else ('F' if r == 'W' else r)
        prz_key = r if r in prize_table else ('F' if r == 'W' else r)

        exp_points += p_exit * points_table.get(pts_key, 0)
        exp_prize += p_exit * prize_table.get(prz_key, 0)

    roi = (exp_prize - entry_cost) / entry_cost if entry_cost > 0 else float('inf')

    return {
        'category': category,
        'surface': surface,
        'player_rank': player_rank,
        'expected_prize': round(exp_prize, 2),
        'expected_points': round(exp_points, 2),
        'entry_cost': entry_cost,
        'expected_profit': round(exp_prize - entry_cost, 2),
        'roi': round(roi, 4) if entry_cost > 0 else None,
        'round_probs': round_probs,
    }


# ==============================================================================
# DEMO
# ==============================================================================
if __name__ == '__main__':
    print("=" * 70)
    print("TOURNAMENT ECONOMICS")
    print("=" * 70)

    # Show points tables
    print("\n--- ATP Ranking Points by Category ---\n")
    for cat in ["Grand Slam", "ATP 1000 (96)", "ATP 500 (32)", "ATP 250 (32)",
                "Challenger 100", "M25", "M15"]:
        pts = ATP_RANKING_POINTS[cat]
        rounds = [r for r in ['1/128','1/64','1/32','1/16','1/8','QF','SF','F','W'] if r in pts]
        vals = [str(pts[r]) for r in rounds]
        print(f"  {cat:<20s}: {' | '.join(f'{r}={v}' for r, v in zip(rounds, vals))}")

    # Compare expected values across tournament types for a rank-200 player
    print(f"\n--- Expected Value Comparison: Rank 200 Player ---\n")
    print(f"{'Category':<25s} {'E[Prize]':>10s} {'E[Points]':>10s} {'E[Profit]':>10s} {'ROI':>8s}")
    print("-" * 70)

    scenarios = [
        ("Grand Slam (Men's)", "Hard", "Grand Slam", 300, 128, 5000),
        ("ATP 1000", "Hard", "Masters 1000", 150, 96, 4000),
        ("ATP 500", "Clay", "ATP 500", 150, 32, 3000),
        ("ATP 250", "Hard", "ATP 250", 200, 32, 2500),
        ("Challenger 125", "Clay", "Challenger", 300, 32, 1500),
        ("Challenger 80", "Hard", "Challenger", 350, 32, 1200),
        ("M25", "Clay", "ITF", 500, 32, 800),
        ("M15", "Hard", "ITF", 600, 32, 500),
    ]

    for cat, surf, tier, med_field, draw, cost in scenarios:
        ev = tournament_expected_value(
            player_rank=200, category=cat, surface=surf,
            tier_group=tier, median_field_rank=med_field,
            draw_size=draw, entry_cost=cost, n_sims=20000, seed=42
        )
        print(f"  {cat:<23s} ${ev['expected_prize']:>9,.0f} {ev['expected_points']:>9.1f}"
              f"  ${ev['expected_profit']:>9,.0f} {100*ev['roi']:>6.1f}%")

    print(f"\nDone!")
