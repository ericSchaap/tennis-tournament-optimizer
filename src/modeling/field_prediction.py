"""
Tennis Tournament Optimizer - Historical Field Prediction
==========================================================

Estimates the likely field for a tournament based on historical
participation patterns. Players tend to return to the same tournaments
year after year, especially when defending points from deep runs.

Key findings from data analysis (2018-2025 ATP):
  - Challenger return rate: 27-29% of field returns year-over-year
  - ATP 1000 return rate: 60%
  - Players reaching finals return 28% vs 19% for R1 losers
  - Field strength (median rank) correlates r=0.61 year-over-year

Two uses:
  1. Predict field strength for a future tournament (better than
     category-average fallback)
  2. Estimate which specific players might enter (useful for the
     user to see familiar names and assess realistic competition)

Usage:
    from field_prediction import FieldPredictor

    predictor = FieldPredictor()
    predictor.load('data/processed/atp_clean_both_ranked.csv')

    # Get predicted field for a tournament
    field = predictor.predict_field('Bordeaux Challenger', year=2025)
    # Returns: {'median_rank': 285, 'p25': 180, 'p75': 420,
    #           'likely_returners': [...], 'predicted_strength': 'moderate'}

    # Get field as a list of opponent ranks for simulation
    ranks = predictor.generate_field_ranks('Bordeaux Challenger',
                                            year=2025, draw_size=32)
"""

import pandas as pd
import numpy as np
import os


# Return rate boost by deepest round reached (empirical)
# Players who went deeper are more likely to return
RETURN_BOOST_BY_ROUND = {
    '1/64': 0.8,   # Less likely (barely participated)
    '1/32': 0.9,
    '1/16': 1.0,   # Baseline
    '1/8':  1.1,
    'QF':   1.25,
    'SF':   1.35,
    'F':    1.45,
    'W':    1.55,   # Winners most likely to return (defending title)
}

ROUND_ORDER = {
    '1/64': 0, '1/32': 1, '1/16': 2, '1/8': 3,
    'QF': 4, 'SF': 5, 'F': 6, 'W': 7,
}

# Base return rates by category (empirical)
BASE_RETURN_RATES = {
    'M15': 0.16,
    'M25': 0.22,
    'Challenger 50': 0.27,
    'Challenger 75': 0.27,
    'Challenger 80': 0.27,
    'Challenger 100': 0.28,
    'Challenger 125': 0.29,
    'Challenger 175': 0.30,
    'ATP 250': 0.34,
    'ATP 500': 0.43,
    'ATP 1000': 0.60,
}


class FieldPredictor:
    """
    Predicts tournament fields based on historical participation data.
    """

    def __init__(self):
        self.tournament_history = {}  # tournament_name -> list of yearly fields
        self.loaded = False

    def load(self, clean_data_path, min_year=2018):
        """
        Load historical participation data from the processed match file.

        Args:
            clean_data_path: Path to atp_clean_both_ranked.csv
            min_year: Earliest year to consider
        """
        cols = ['player_id', 'tournament_name', 'category', 'year',
                'level', 'player_rank', 'player_rank_type', 'round']
        df = pd.read_csv(clean_data_path, usecols=cols, low_memory=False)
        df = df[(df['level'] == 'pro') &
                (df['player_rank_type'] == 'pro') &
                (df['year'] >= min_year)]

        # One entry per player-tournament-year with best round
        entries = df.groupby(['player_id', 'tournament_name', 'year']).agg(
            rank=('player_rank', 'median'),
            category=('category', 'first'),
            best_round=('round', lambda x: max(x, key=lambda r: ROUND_ORDER.get(r, 0))),
        ).reset_index()

        # Build tournament history
        for tname, group in entries.groupby('tournament_name'):
            yearly = {}
            for year, ygroup in group.groupby('year'):
                players = []
                for _, row in ygroup.iterrows():
                    players.append({
                        'player_id': row['player_id'],
                        'rank': row['rank'],
                        'best_round': row['best_round'],
                    })
                yearly[year] = {
                    'players': players,
                    'category': ygroup['category'].iloc[0],
                    'median_rank': ygroup['rank'].median(),
                    'p25_rank': ygroup['rank'].quantile(0.25),
                    'p75_rank': ygroup['rank'].quantile(0.75),
                    'n_players': len(players),
                }
            self.tournament_history[tname] = yearly

        self.loaded = True
        print(f"    Field predictor loaded: {len(self.tournament_history):,} tournaments, "
              f"years {min_year}-{entries['year'].max()}")

    def predict_field(self, tournament_name, year, lookback_years=3):
        """
        Predict the field for a tournament in a given year.

        Uses historical data to estimate:
          - Field strength (median, P25, P75 rank)
          - Likely returning players (with probabilities)
          - Overall strength classification

        Args:
            tournament_name: Name of the tournament
            year: Year to predict for
            lookback_years: How many past years to consider

        Returns:
            dict with field predictions, or None if no history
        """
        if tournament_name not in self.tournament_history:
            return None

        history = self.tournament_history[tournament_name]
        recent_years = sorted([y for y in history.keys()
                               if year - lookback_years <= y < year],
                              reverse=True)

        if not recent_years:
            return None

        # Field strength: weighted average of recent years (most recent = highest weight)
        total_weight = 0
        weighted_median = 0
        weighted_p25 = 0
        weighted_p75 = 0
        all_field_sizes = []

        for i, y in enumerate(recent_years):
            weight = lookback_years - i  # Most recent gets highest weight
            ydata = history[y]
            weighted_median += ydata['median_rank'] * weight
            weighted_p25 += ydata['p25_rank'] * weight
            weighted_p75 += ydata['p75_rank'] * weight
            all_field_sizes.append(ydata['n_players'])
            total_weight += weight

        pred_median = weighted_median / total_weight
        pred_p25 = weighted_p25 / total_weight
        pred_p75 = weighted_p75 / total_weight
        category = history[recent_years[0]]['category']

        # Likely returners: players from most recent year with return probability
        base_rate = BASE_RETURN_RATES.get(category, 0.25)
        # Category fuzzy match
        if base_rate == 0.25:
            for key, rate in BASE_RETURN_RATES.items():
                if key in category:
                    base_rate = rate
                    break

        likely_returners = []
        if recent_years:
            last_year = history[recent_years[0]]
            for player in last_year['players']:
                round_boost = RETURN_BOOST_BY_ROUND.get(
                    player['best_round'], 1.0)
                return_prob = min(0.9, base_rate * round_boost)

                likely_returners.append({
                    'player_id': player['player_id'],
                    'last_rank': player['rank'],
                    'best_round': player['best_round'],
                    'return_probability': round(return_prob, 2),
                })

        likely_returners.sort(key=lambda x: -x['return_probability'])

        # Strength classification
        if pred_median <= 200:
            strength = 'very_strong'
        elif pred_median <= 350:
            strength = 'strong'
        elif pred_median <= 500:
            strength = 'moderate'
        elif pred_median <= 800:
            strength = 'weak'
        else:
            strength = 'very_weak'

        return {
            'tournament_name': tournament_name,
            'category': category,
            'predicted_year': year,
            'years_of_history': len(recent_years),
            'median_rank': round(pred_median),
            'p25_rank': round(pred_p25),
            'p75_rank': round(pred_p75),
            'avg_field_size': round(np.mean(all_field_sizes)),
            'predicted_strength': strength,
            'likely_returners': likely_returners,
            'base_return_rate': base_rate,
        }

    def generate_field_ranks(self, tournament_name, year, draw_size=32,
                             seed=None):
        """
        Generate a list of opponent ranks for tournament simulation.

        Combines predicted returning players with category-appropriate
        random fills for the remaining slots.

        Args:
            tournament_name: Tournament to predict for
            year: Year to predict
            draw_size: Size of the draw
            seed: Random seed

        Returns:
            list of int ranks, sorted ascending (strongest first)
        """
        import random
        rng = random.Random(seed)

        prediction = self.predict_field(tournament_name, year)

        if prediction is None:
            # No history — fall back to category-based generation
            return None

        field = []

        # Add returning players (probabilistic)
        for player in prediction['likely_returners']:
            if rng.random() < player['return_probability']:
                # Player returns, possibly with shifted rank (±15%)
                rank_shift = rng.gauss(0, player['last_rank'] * 0.10)
                new_rank = max(1, int(player['last_rank'] + rank_shift))
                field.append(new_rank)

            if len(field) >= draw_size:
                break

        # Fill remaining slots with random players matching field profile
        remaining = draw_size - len(field)
        if remaining > 0:
            median = prediction['median_rank']
            p25 = prediction['p25_rank']
            p75 = prediction['p75_rank']
            spread = (p75 - p25) * 0.5

            for _ in range(remaining):
                rank = max(1, int(rng.gauss(median, spread)))
                field.append(rank)

        field.sort()
        return field[:draw_size]

    def get_defense_tournaments(self, player_id, year, min_points=5):
        """
        Find tournaments where a player has points to defend.

        Args:
            player_id: Player to check
            year: Year to look at (checks year-1 for expiring results)
            min_points: Minimum points to flag

        Returns:
            list of dicts with tournament info and points at stake
        """
        from tournament_economics import get_points_table

        defense = []
        prev_year = year - 1

        for tname, history in self.tournament_history.items():
            if prev_year not in history:
                continue

            ydata = history[prev_year]
            for player in ydata['players']:
                if player['player_id'] != player_id:
                    continue

                # Look up points for their best round
                pts_table = get_points_table(ydata['category'])
                if pts_table:
                    points = pts_table.get(player['best_round'], 0)
                    # Check winner points
                    if player['best_round'] == 'F':
                        # They might have won (F is last round in our data for some)
                        points = max(points, pts_table.get('W', 0))
                else:
                    points = 0

                if points >= min_points:
                    defense.append({
                        'tournament_name': tname,
                        'category': ydata['category'],
                        'year_played': prev_year,
                        'best_round': player['best_round'],
                        'points_to_defend': points,
                        'rank_at_time': player['rank'],
                    })

        defense.sort(key=lambda x: -x['points_to_defend'])
        return defense


# =========================================================================
# DEMO
# =========================================================================
if __name__ == '__main__':
    print("Field Prediction Module - Demo")
    print("=" * 55)

    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    data_path = os.path.join(base, 'data', 'processed',
                             'atp_clean_both_ranked.csv')

    if not os.path.exists(data_path):
        print("  Data not found — skipping demo.")
    else:
        predictor = FieldPredictor()
        predictor.load(data_path)

        # Predict field for a well-known Challenger
        for tname in ['Bordeaux Challenger', 'Campinas Challenger',
                      'Heilbronn Challenger']:
            pred = predictor.predict_field(tname, year=2025)
            if pred:
                print(f"\n  {tname} (2025 prediction):")
                print(f"    Category: {pred['category']}")
                print(f"    Strength: {pred['predicted_strength']} "
                      f"(median rank {pred['median_rank']})")
                print(f"    Field: P25={pred['p25_rank']}, "
                      f"median={pred['median_rank']}, P75={pred['p75_rank']}")
                print(f"    Avg field size: {pred['avg_field_size']}")
                print(f"    Top 5 likely returners:")
                for r in pred['likely_returners'][:5]:
                    print(f"      Player {r['player_id']:>6d}: "
                          f"rank {r['last_rank']:>4.0f}, "
                          f"reached {r['best_round']:<4s}, "
                          f"{r['return_probability']:.0%} return prob")

        # Generate a simulated field
        print(f"\n  Simulated 32-draw field for Bordeaux Challenger 2025:")
        ranks = predictor.generate_field_ranks('Bordeaux Challenger',
                                                year=2025, draw_size=32,
                                                seed=42)
        if ranks:
            print(f"    Ranks: {ranks}")
            print(f"    Median: {np.median(ranks):.0f}, "
                  f"min: {min(ranks)}, max: {max(ranks)}")
