"""
Seedr Validation Suite
=======================

Runs three validation tests against hold-out data:
  1. Win probability model calibration
  2. Tournament simulation calibration (with field predictor)
  3. Schedule recommendation quality (with points expiry)

Usage:
    cd tennis-tournament-optimizer
    python src/modeling/run_validation.py

    # Or with custom parameters:
    python src/modeling/run_validation.py --year 2024 --n-sim-entries 2000 --n-schedule-players 8

Requirements:
    - Processed data must exist (run 00_unified_pipeline.py first)
    - All modeling modules must be in src/modeling/

Output:
    - Prints results to console
    - Saves JSON results to outputs/validation_results.json
"""

import sys
import os
import time
import json
import argparse

# Add modeling directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
BASE_DIR = os.path.join(SCRIPT_DIR, '..', '..')

import pandas as pd
import numpy as np

from win_probability import WinProbabilityModel, CATEGORY_TO_TIER
from seasonal_optimizer import SeasonalOptimizer, TournamentSimulator
from field_prediction import FieldPredictor
from points_to_rank import PointsRankMapper
from points_expiry import PointsExpiryTracker
from travel_costs import COUNTRY_CONTINENT


ROUND_ORDER = {
    '1/64': 0, '1/32': 1, '1/16': 2, '1/8': 3,
    'QF': 4, 'SF': 5, 'F': 6, 'W': 7,
}

# Country name to IOC code mapping for profiles
COUNTRY_FIX = {
    'United States of America': 'USA', 'Australia': 'AUS',
    'New Zealand': 'NZL', 'Spain': 'ESP', 'France': 'FRA',
    'Kazakhstan': 'KAZ', 'Portugal': 'POR', 'Belgium': 'BEL',
    'Romania': 'ROU', 'Germany': 'GER', 'Serbia': 'SRB',
    'Ukraine': 'UKR', 'Italy': 'ITA', 'Czech Republic': 'CZE',
    'Argentina': 'ARG', 'Croatia': 'CRO', 'Japan': 'JPN',
    'South Korea': 'KOR', 'Brazil': 'BRA', 'Colombia': 'COL',
    'Netherlands': 'NED', 'Sweden': 'SWE', 'Great Britain': 'GBR',
}


# =========================================================================
# TEST 1: Win Probability Model
# =========================================================================
def test_win_probability(df, year=2024):
    """
    Test win probability calibration on pro-vs-pro matches.

    Args:
        df: Full processed DataFrame
        year: Hold-out year for testing

    Returns:
        dict with calibration results
    """
    print(f"\n{'='*60}")
    print(f"TEST 1: WIN PROBABILITY MODEL (year={year})")
    print(f"{'='*60}")
    t0 = time.time()

    test = df[(df['year'] == year) & (df['level'] == 'pro') &
              (df['match_status'] == 'completed') &
              (df['ranking_match_type'] == 'both_pro') &
              (df['result'].isin(['W', 'L']))].copy()

    print(f"  Test set: {len(test):,} matches")

    win_model = WinProbabilityModel()

    preds = []
    for _, m in test.iterrows():
        tier = CATEGORY_TO_TIER.get(m['category'], 'Challenger')
        p = win_model.predict(m['player_rank'], m['opponent_rank'],
                              m['surface'], tier)
        preds.append(p)

    test['pred'] = preds
    test['actual'] = (test['result'] == 'W').astype(float)

    overall_brier = float(((test['pred'] - test['actual'])**2).mean())

    # Calibration buckets
    buckets = []
    max_gap = 0
    for lo, hi in [(0, .15), (.15, .25), (.25, .35), (.35, .45), (.45, .55),
                   (.55, .65), (.65, .75), (.75, .85), (.85, 1.01)]:
        mask = (test['pred'] >= lo) & (test['pred'] < hi)
        if mask.sum() < 30:
            continue
        avg_p = float(test.loc[mask, 'pred'].mean())
        avg_a = float(test.loc[mask, 'actual'].mean())
        gap = avg_a - avg_p
        if abs(gap) > abs(max_gap):
            max_gap = gap
        buckets.append({
            'range': f'{lo:.0%}-{hi:.0%}',
            'predicted': round(avg_p, 3),
            'actual': round(avg_a, 3),
            'gap': round(gap, 3),
            'n': int(mask.sum()),
        })

    # By tier
    by_tier = []
    for tier_pat, label in [('M15', 'M15'), ('M25', 'M25'),
                            ('Challenger 50|Challenger 75', 'Challenger 50-75'),
                            ('Challenger 100|Challenger 125', 'Challenger 100-125'),
                            ('ATP 250', 'ATP 250'), ('ATP 500', 'ATP 500'),
                            ('ATP 1000', 'ATP 1000')]:
        mask = test['category'].str.contains(tier_pat, na=False)
        sub = test[mask]
        if len(sub) < 50:
            continue
        brier = float(((sub['pred'] - sub['actual'])**2).mean())
        by_tier.append({
            'tier': label, 'n': int(len(sub)),
            'brier': round(brier, 4),
            'predicted_wr': round(float(sub['pred'].mean()), 3),
            'actual_wr': round(float(sub['actual'].mean()), 3),
        })

    # By surface
    by_surface = []
    for surf in ['Clay', 'Hard', 'Hard Indoor', 'Grass']:
        mask = test['surface'] == surf
        sub = test[mask]
        if len(sub) < 100:
            continue
        brier = float(((sub['pred'] - sub['actual'])**2).mean())
        by_surface.append({
            'surface': surf, 'n': int(len(sub)),
            'brier': round(brier, 4),
        })

    # Print results
    print(f"\n  Overall Brier score: {overall_brier:.4f}")
    print(f"  Max calibration gap: {abs(max_gap):.1%}")
    print(f"\n  Calibration:")
    print(f"    {'Predicted':>10s} {'Actual':>8s} {'Gap':>7s} {'n':>7s}")
    for b in buckets:
        print(f"    {b['predicted']:>9.1%} {b['actual']:>7.1%} "
              f"{b['gap']:>+6.1%} {b['n']:>7,}")

    print(f"\n  By tier:")
    for t in by_tier:
        print(f"    {t['tier']:<22s} Brier={t['brier']:.4f}  n={t['n']:,}")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.0f}s")

    return {
        'n_matches': int(len(test)),
        'overall_brier': round(overall_brier, 4),
        'max_calibration_gap': round(abs(max_gap), 3),
        'calibration_buckets': buckets,
        'by_tier': by_tier,
        'by_surface': by_surface,
    }


# =========================================================================
# TEST 2: Simulation Calibration
# =========================================================================
def test_simulation(df, year=2024, n_entries=2500, n_sims=500):
    """
    Test tournament simulation calibration with historical field predictor.

    Args:
        df: Full processed DataFrame
        year: Hold-out year
        n_entries: Number of player-tournament entries to simulate
        n_sims: Monte Carlo sims per entry

    Returns:
        dict with simulation calibration results
    """
    print(f"\n{'='*60}")
    print(f"TEST 2: SIMULATION CALIBRATION (year={year}, n={n_entries})")
    print(f"{'='*60}")
    t0 = time.time()

    clean_data_path = os.path.join(BASE_DIR, 'data', 'processed',
                                    'atp_clean_both_ranked.csv')

    # Load field predictor
    print("  Loading field predictor...")
    fp = FieldPredictor()
    fp.load(clean_data_path)

    simulator = TournamentSimulator(
        WinProbabilityModel(),
        field_data_path=os.path.join(BASE_DIR, 'models', 'field_profiles.json'),
        category_fallback_path=os.path.join(BASE_DIR, 'models',
                                             'category_field_fallbacks.json'),
        name_to_key_path=os.path.join(BASE_DIR, 'models',
                                       'tournament_name_to_key.json'),
        field_predictor=fp)

    # 2024 pro-vs-pro
    df_test = df[(df['year'] == year) & (df['level'] == 'pro') &
                 (df['match_status'] == 'completed') &
                 (df['player_rank_type'] == 'pro') &
                 (df['opponent_rank_type'] == 'pro')]

    # Field medians
    field_medians = df_test.groupby(['tournament_name', 'category']).agg(
        median_field_rank=('player_rank', 'median'),
        field_p25=('player_rank', lambda x: x.quantile(0.25)),
        field_p75=('player_rank', lambda x: x.quantile(0.75)),
    ).reset_index()

    # Player deepest round per tournament
    player_results = []
    for (pid, tname), group in df_test.groupby(['player_id', 'tournament_name']):
        group = group.copy()
        group['round_num'] = group['round'].map(ROUND_ORDER)
        group = group.sort_values('round_num')
        last = group.iloc[-1]
        if last['result'] == 'W' and last['round'] == 'F':
            deepest = 'W'
        elif last['result'] == 'W':
            nxt = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}
            deepest = {v: k for k, v in ROUND_ORDER.items()}.get(
                nxt.get(ROUND_ORDER.get(last['round'], 0), 0), last['round'])
        else:
            deepest = last['round']

        player_results.append({
            'player_id': pid, 'tournament_name': tname,
            'player_rank': group['player_rank'].iloc[0],
            'category': group['category'].iloc[0],
            'surface': group['surface'].iloc[0],
            'deepest_round': deepest,
            'deepest_round_num': ROUND_ORDER.get(deepest, 0),
        })

    rdf = pd.DataFrame(player_results)
    rdf = rdf.merge(field_medians, on=['tournament_name', 'category'], how='left')

    # Sample target categories
    target = rdf[rdf['category'].str.contains('Challenger|M25|M15|ATP 250',
                                               case=False)]
    sample = target.sample(min(n_entries, len(target)), random_state=42)
    print(f"  Simulating {len(sample):,} entries ({n_sims} sims each)...")

    predictions = []
    for idx, (_, row) in enumerate(sample.iterrows()):
        if (idx + 1) % 500 == 0:
            print(f"    {idx+1}/{len(sample)} ({time.time()-t0:.0f}s)")

        tournament = {
            'tournament_name': row['tournament_name'],
            'category': row['category'],
            'surface': row['surface'],
            'tier_name': CATEGORY_TO_TIER.get(row['category'], 'Challenger'),
            'median_field_rank': row.get('median_field_rank', 300),
            'field_p25': row.get('field_p25', 150),
            'field_p75': row.get('field_p75', 500),
            'draw_size': 128 if 'Grand Slam' in row['category'] else
                         64 if 'ATP 500' in row['category'] else 32,
            'start_dt': pd.Timestamp(year=year, month=6, day=1),
        }

        ev = simulator.estimate_ev(row['player_rank'], tournament,
                                    n_sims=n_sims, seed=idx)
        round_probs = ev['round_probs']

        cum_probs = {}
        for r in ['1/16', '1/8', 'QF', 'SF', 'F', 'W']:
            rnum = ROUND_ORDER[r]
            cum_probs[r] = sum(p for rn, p in round_probs.items()
                               if ROUND_ORDER.get(rn, 0) >= rnum)

        predictions.append({
            'player_rank': row['player_rank'],
            'category': row['category'],
            'actual_round_num': row['deepest_round_num'],
            **{f'pred_{r}': cum_probs.get(r, 0)
               for r in ['1/8', 'QF', 'SF', 'F', 'W']},
        })

    pred_df = pd.DataFrame(predictions)

    # Calibration per round
    rounds_results = {}
    for round_name in ['1/8', 'QF', 'SF', 'F', 'W']:
        rnum = ROUND_ORDER[round_name]
        actual = (pred_df['actual_round_num'] >= rnum).astype(float)
        predicted = pred_df[f'pred_{round_name}']
        brier = float(((predicted - actual)**2).mean())

        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.85, 1.01]
        pred_df['_bin'] = pd.cut(predicted, bins=bins)
        max_gap = 0
        buckets = []

        for b in pred_df['_bin'].cat.categories:
            mask = pred_df['_bin'] == b
            if mask.sum() < 10:
                continue
            avg_p = float(predicted[mask].mean())
            avg_a = float(actual[mask].mean())
            gap = avg_a - avg_p
            if abs(gap) > abs(max_gap):
                max_gap = gap
            buckets.append({
                'predicted': round(avg_p, 3), 'actual': round(avg_a, 3),
                'gap': round(gap, 3), 'n': int(mask.sum()),
            })

        rounds_results[round_name] = {
            'brier': round(brier, 4),
            'max_gap': round(abs(max_gap), 3),
            'buckets': buckets,
        }

    # By category
    by_category = []
    for cat_group in ['Challenger', 'M25', 'M15', 'ATP 250']:
        sub = pred_df[pred_df['category'].str.contains(cat_group, case=False)]
        if len(sub) < 50:
            continue
        rnum = ROUND_ORDER['QF']
        actual = (sub['actual_round_num'] >= rnum).astype(float)
        predicted = sub['pred_QF']
        brier = float(((predicted - actual)**2).mean())
        by_category.append({
            'category': cat_group, 'n': int(len(sub)),
            'brier_qf': round(brier, 4),
            'pred_qf': round(float(predicted.mean()), 3),
            'actual_qf': round(float(actual.mean()), 3),
        })

    # Print results
    print(f"\n  Results:")
    for rnd, data in rounds_results.items():
        print(f"    Reach {rnd:>3s}+: Brier={data['brier']:.4f}, "
              f"Max gap={data['max_gap']:.1%}")

    print(f"\n  By category (QF reach):")
    for c in by_category:
        print(f"    {c['category']:<15s}: Brier={c['brier_qf']:.4f}, "
              f"Pred={c['pred_qf']:.1%}, Actual={c['actual_qf']:.1%}")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.0f}s")

    return {
        'n_entries': int(len(sample)),
        'n_sims': n_sims,
        'rounds': rounds_results,
        'by_category': by_category,
    }


# =========================================================================
# TEST 3: Schedule Quality
# =========================================================================
def test_schedules(df, profiles, year=2024, n_players=8):
    """
    Compare optimizer recommendations to actual player schedules.

    Args:
        df: Full processed DataFrame
        profiles: Player profiles DataFrame
        year: Year to test
        n_players: Number of test players

    Returns:
        dict with schedule comparison results
    """
    print(f"\n{'='*60}")
    print(f"TEST 3: SCHEDULE QUALITY (year={year}, n_players={n_players})")
    print(f"{'='*60}")
    t0 = time.time()

    mapper = PointsRankMapper()
    clean_data_path = os.path.join(BASE_DIR, 'data', 'processed',
                                    'atp_clean_both_ranked.csv')

    df_year = df[(df['year'] == year) & (df['level'] == 'pro')].copy()
    df_year['start_dt'] = pd.to_datetime(df_year['start_date_parsed'])
    df_year['week'] = df_year['start_dt'].dt.isocalendar().week.astype(int)
    window = df_year[(df_year['week'] >= 14) & (df_year['week'] <= 24)]

    # Previous year for points expiry
    df_prev = df[(df['year'] == year - 1) & (df['level'] == 'pro')].copy()
    df_prev['start_dt'] = pd.to_datetime(df_prev['start_date_parsed'])
    df_prev['week'] = df_prev['start_dt'].dt.isocalendar().week.astype(int)

    # Select test players
    ps = window.groupby('player_id').agg(
        avg_rank=('player_rank', 'median'),
        n_tourn=('tournament_name', 'nunique'),
    ).reset_index()
    ps = ps.merge(
        profiles[['player_id', 'country']].rename(columns={'country': 'pc'}),
        on='player_id', how='left')
    ps = ps[(ps['n_tourn'] >= 5) &
            ps['pc'].apply(lambda c: isinstance(c, str))]

    test_players = []
    seen = set()
    for _, r in ps.sort_values('n_tourn', ascending=False).iterrows():
        bucket = (int(r['avg_rank']) // 150) * 150
        if bucket in seen or len(test_players) >= n_players:
            continue
        c = r['pc']
        c = COUNTRY_FIX.get(c, c[:3].upper() if len(c) > 3 else c)
        seen.add(bucket)
        test_players.append({
            'pid': r['player_id'],
            'rank': int(r['avg_rank']),
            'country': c,
        })

    print(f"  Selected {len(test_players)} test players")

    results_list = []
    for i, p in enumerate(test_players):
        pid, rank, country = p['pid'], p['rank'], p['country']
        points = mapper.rank_to_points(rank)

        # Actual schedule
        actual = window[window['player_id'] == pid].sort_values('week')
        asched = actual.groupby(
            ['tournament_name', 'category', 'week', 'surface', 'country']
        ).agg(
            best_round=('round',
                        lambda x: max(x, key=lambda r: ROUND_ORDER.get(r, 0))),
        ).reset_index().sort_values('week')
        n_act = len(asched)
        if n_act < 3:
            continue

        act_names = set(asched['tournament_name'])
        act_clay = float((asched['surface'] == 'Clay').mean())
        ac = [c for c in asched['country'] if isinstance(c, str)]
        act_cont = [COUNTRY_CONTINENT.get(c, '?') for c in ac]
        act_sw = sum(1 for j in range(1, len(act_cont))
                     if act_cont[j] != act_cont[j-1])
        act_start_rk = actual['player_rank'].iloc[0]
        act_end_rk = actual['player_rank'].iloc[-1]

        # Points expiry from previous year
        prev = df_prev[(df_prev['player_id'] == pid) &
                       (df_prev['week'] >= 14) & (df_prev['week'] <= 24)]
        tracker = PointsExpiryTracker(current_total_points=points)
        if len(prev) > 0:
            prev_sched = prev.groupby(
                ['tournament_name', 'category', 'week']
            ).agg(
                best_round=('round',
                            lambda x: max(x, key=lambda r: ROUND_ORDER.get(r, 0))),
            ).reset_index()
            for _, row in prev_sched.iterrows():
                tracker.add_tournament_result(
                    int(row['week']), row['category'], row['best_round'])

        # Run optimizer
        opt = SeasonalOptimizer(player_country=country)
        opt.load_calendar(clean_data_path, year=year)

        res = opt.optimize(
            player_rank=rank, player_points=points,
            planning_start_week=14, planning_end_week=24,
            n_schedules=80, n_sims_per_tournament=150,
            n_sims_per_schedule=200,
            target_tournaments=n_act,
            max_continent_switches=max(1, act_sw),
            points_expiry_tracker=tracker,
            seed=42, verbose=False)

        if 'error' in res:
            continue

        top = res['top_schedules'][0]
        rec_names = set(top['tournaments'])
        overlap = rec_names & act_names
        rs = [t.get('surface', '?') for _, t in top['schedule']]
        rec_clay = sum(1 for s in rs if s == 'Clay') / max(len(rs), 1)
        rc = [str(t.get('country', '?')) for _, t in top['schedule']]
        rec_cont = [COUNTRY_CONTINENT.get(c, '?') for c in rc]
        rec_sw = sum(1 for j in range(1, len(rec_cont))
                     if rec_cont[j] != rec_cont[j-1])

        results_list.append({
            'rank': rank, 'country': country,
            'n_act': n_act, 'n_rec': len(top['schedule']),
            'overlap': len(overlap),
            'overlap_pct': round(len(overlap) / max(n_act, 1), 2),
            'matching': sorted(list(overlap)),
            'act_clay': round(act_clay, 2),
            'rec_clay': round(rec_clay, 2),
            'act_switches': act_sw, 'rec_switches': rec_sw,
            'act_rank_change': int(act_start_rk - act_end_rk),
            'pred_rank_change': round(rank - top['expected_final_rank']),
            'expiry_tracked_pts': tracker.get_tracked_total(),
        })
        print(f"    {i+1}/{len(test_players)}: rank {rank} {country} "
              f"({time.time()-t0:.0f}s)")

    # Aggregates
    if len(results_list) > 0:
        ol = [r['overlap_pct'] for r in results_list]
        cg = [abs(r['act_clay'] - r['rec_clay']) for r in results_list]
        re = [r['pred_rank_change'] - r['act_rank_change']
              for r in results_list]
        pdr = [r['pred_rank_change'] for r in results_list]
        adr = [r['act_rank_change'] for r in results_list]
        corr = float(np.corrcoef(pdr, adr)[0, 1]) if len(results_list) > 2 else 0

        aggregates = {
            'n_players': len(results_list),
            'overlap_median': round(float(np.median(ol)), 2),
            'overlap_mean': round(float(np.mean(ol)), 2),
            'clay_gap_median': round(float(np.median(cg)), 2),
            'rec_switches': sum(r['rec_switches'] for r in results_list),
            'act_switches': sum(r['act_switches'] for r in results_list),
            'rank_error_median': round(float(np.median(re))),
            'rank_error_mean': round(float(np.mean(re))),
            'rank_correlation': round(corr, 2),
        }
    else:
        aggregates = {'n_players': 0}

    # Print results
    print(f"\n  Per-player results:")
    print(f"    {'Rank':>5s} {'Cty':>4s} {'Overlap':>9s} {'Clay':>9s} "
          f"{'Sw':>5s} {'ΔRank':>12s}")
    for r in results_list:
        print(f"    {r['rank']:>5d} {r['country']:>4s} "
              f"{r['overlap']}/{r['n_act']}({r['overlap_pct']:>3.0%})  "
              f"{r['act_clay']:.0%}/{r['rec_clay']:.0%}  "
              f"{r['act_switches']}/{r['rec_switches']}  "
              f"{r['act_rank_change']:>+5d}/{r['pred_rank_change']:>+5.0f}")

    print(f"\n  Aggregates:")
    for k, v in aggregates.items():
        print(f"    {k}: {v}")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.0f}s")

    return {
        'players': results_list,
        'aggregates': aggregates,
    }


# =========================================================================
# MAIN
# =========================================================================
def main():
    parser = argparse.ArgumentParser(description='Seedr Validation Suite')
    parser.add_argument('--year', type=int, default=2024,
                        help='Hold-out year for testing (default: 2024)')
    parser.add_argument('--n-sim-entries', type=int, default=2500,
                        help='Number of simulation entries (default: 2500)')
    parser.add_argument('--n-sims', type=int, default=500,
                        help='Monte Carlo sims per entry (default: 500)')
    parser.add_argument('--n-schedule-players', type=int, default=8,
                        help='Number of players for schedule test (default: 8)')
    parser.add_argument('--skip-simulation', action='store_true',
                        help='Skip simulation test (slow)')
    parser.add_argument('--skip-schedules', action='store_true',
                        help='Skip schedule test (slow)')
    args = parser.parse_args()

    t_total = time.time()

    # Load data
    clean_data_path = os.path.join(BASE_DIR, 'data', 'processed',
                                    'atp_clean_both_ranked.csv')
    profiles_path = os.path.join(BASE_DIR, 'data', 'raw', 'atp',
                                  'atp_player_profiles.csv.gz')

    print("Loading data...")
    df = pd.read_csv(clean_data_path, low_memory=False)
    profiles = pd.read_csv(profiles_path)
    print(f"  Loaded {len(df):,} matches")

    all_results = {'year': args.year, 'timestamp': time.strftime('%Y-%m-%d %H:%M')}

    # Test 1: Win probability
    all_results['win_probability'] = test_win_probability(df, year=args.year)

    # Test 2: Simulation calibration
    if not args.skip_simulation:
        all_results['simulation'] = test_simulation(
            df, year=args.year,
            n_entries=args.n_sim_entries, n_sims=args.n_sims)
    else:
        print("\n  [Skipping simulation test]")

    # Test 3: Schedule quality
    if not args.skip_schedules:
        all_results['schedules'] = test_schedules(
            df, profiles, year=args.year,
            n_players=args.n_schedule_players)
    else:
        print("\n  [Skipping schedule test]")

    # Save results
    output_dir = os.path.join(BASE_DIR, 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'validation_results.json')
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved to {output_path}")

    total_time = time.time() - t_total
    print(f"\n{'='*60}")
    print(f"VALIDATION COMPLETE ({total_time:.0f}s)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
