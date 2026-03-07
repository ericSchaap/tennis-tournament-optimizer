"""
Tennis Tournament Optimizer - Synthetic Ranks for Unranked Players
==================================================================

Assigns synthetic ranking values to players who have no ATP/WTA ranking.
These are typically local players, college players, or juniors without
pro rankings who appear at M15/M25 events.

Calibrated from empirical loss rates: when a ranked player (avg ~800)
faces an unranked opponent at M15, they lose about 14% of the time.
This loss rate corresponds to an effective rank of approximately 2500.

Usage in the pipeline:
    from synthetic_ranks import assign_synthetic_rank

    # After ranking join, for rows where opponent has no ranking:
    df.loc[df['opponent_rank'].isna(), 'opponent_rank'] = df.loc[
        df['opponent_rank'].isna(), 'category'].apply(
            lambda cat: get_synthetic_rank(cat))
    df.loc[df['opponent_rank_was_synthetic'], 'opponent_rank_type'] = 'synthetic'
"""


# =========================================================================
# SYNTHETIC RANK VALUES BY TIER
# =========================================================================
# Calibrated from ranked-vs-unranked loss rates (2020-2025 ATP data)
#
# Method: For each tier, measured the loss rate of ranked players against
# unranked opponents. Then found the opponent rank that produces the same
# loss rate in ranked-vs-ranked matches.
#
# M15:  14% loss rate -> equivalent to rank ~2500
# M25:  14% loss rate -> equivalent to rank ~2500
# Challengers: <2% unranked opponents, negligible impact
# ATP:  <1% unranked opponents, negligible impact

SYNTHETIC_RANKS = {
    # ITF level: ~19% of opponents are unranked
    'M15': 2500,
    'M25': 2500,
    # Challengers: ~1-2% unranked, assign conservatively
    'Challenger 50': 2000,
    'Challenger 75': 2000,
    'Challenger 80': 2000,
    'Challenger 90': 2000,
    'Challenger 100': 2000,
    'Challenger 110': 2000,
    'Challenger 125': 2000,
    'Challenger 175': 1800,
    # ATP: essentially no unranked players, but just in case
    'ATP 250': 1500,
    'ATP 500': 1500,
    'ATP 1000': 1500,
}

# Share of the draw that is typically unranked (for field generation)
UNRANKED_SHARE = {
    'M15': 0.19,
    'M25': 0.18,
    'Challenger 50': 0.02,
    'Challenger 75': 0.01,
    'Challenger 80': 0.01,
    'Challenger 90': 0.01,
    'Challenger 100': 0.01,
    'Challenger 125': 0.01,
    'Challenger 175': 0.01,
    'ATP 250': 0.005,
    'ATP 500': 0.005,
    'ATP 1000': 0.005,
}


def get_synthetic_rank(category):
    """
    Get the synthetic rank to assign to an unranked player
    at a given tournament category.

    Args:
        category: Tournament category string (e.g., "M15", "Challenger 75")

    Returns:
        int: Synthetic rank value
    """
    if not isinstance(category, str):
        return 2500  # Default

    # Exact match
    if category in SYNTHETIC_RANKS:
        return SYNTHETIC_RANKS[category]

    # Partial match
    for key, rank in SYNTHETIC_RANKS.items():
        if key in category:
            return rank

    # Fallback by tier group
    cat_lower = category.lower()
    if 'm15' in cat_lower or 'w15' in cat_lower or 'w10' in cat_lower:
        return 2500
    elif 'm25' in cat_lower or 'w25' in cat_lower or 'w35' in cat_lower:
        return 2500
    elif 'challenger' in cat_lower:
        return 2000
    elif 'atp' in cat_lower or 'wta' in cat_lower:
        return 1500
    else:
        return 2500


def get_unranked_share(category):
    """
    Get the typical share of unranked players in a draw
    for a given tournament category.

    Args:
        category: Tournament category string

    Returns:
        float: Share of draw that is unranked (0-1)
    """
    if not isinstance(category, str):
        return 0.0

    if category in UNRANKED_SHARE:
        return UNRANKED_SHARE[category]

    for key, share in UNRANKED_SHARE.items():
        if key in category:
            return share

    cat_lower = category.lower()
    if 'm15' in cat_lower or 'w15' in cat_lower:
        return 0.19
    elif 'm25' in cat_lower or 'w25' in cat_lower:
        return 0.18
    elif 'challenger' in cat_lower:
        return 0.01
    else:
        return 0.0


def assign_synthetic_ranks(df, rank_col='opponent_rank',
                           category_col='category',
                           rank_type_col='opponent_rank_type'):
    """
    Assign synthetic ranks to unranked players in a DataFrame.
    Adds a boolean column indicating which rows were modified.

    This function is designed to be called in the pipeline after
    the ranking join, before filtering to both-ranked.

    Args:
        df: DataFrame with match data
        rank_col: Column containing the rank (may have NaNs)
        category_col: Column with tournament category
        rank_type_col: Column with ranking type (pro/junior/None)

    Returns:
        df: Modified DataFrame with synthetic ranks filled in
            and a new '{rank_col}_synthetic' boolean column
    """
    import pandas as pd

    synthetic_col = f'{rank_col}_synthetic'
    is_missing = df[rank_col].isna()

    df[synthetic_col] = False
    df.loc[is_missing, rank_col] = df.loc[is_missing, category_col].apply(
        get_synthetic_rank).astype(float)
    df.loc[is_missing, rank_type_col] = 'synthetic'
    df.loc[is_missing, synthetic_col] = True

    n_filled = is_missing.sum()
    if n_filled > 0:
        print(f"    Assigned synthetic ranks to {n_filled:,} unranked entries "
              f"({100*n_filled/len(df):.1f}%)")

    return df


# =========================================================================
# DEMO
# =========================================================================
if __name__ == '__main__':
    print("Synthetic Ranks Module - Demo")
    print("=" * 50)

    for cat in ['M15', 'M25', 'Challenger 50', 'Challenger 75',
                'Challenger 125', 'ATP 250']:
        rank = get_synthetic_rank(cat)
        share = get_unranked_share(cat)
        print(f"  {cat:<20s} rank={rank:>5d}, {share:.0%} of draw unranked")

    print(f"\nIn a 32-draw M15:")
    n_unranked = int(32 * get_unranked_share('M15'))
    n_ranked = 32 - n_unranked
    print(f"  ~{n_ranked} ranked players + ~{n_unranked} unranked (synth rank {get_synthetic_rank('M15')})")

    print(f"\nIn a 32-draw Challenger 75:")
    n_unranked = int(32 * get_unranked_share('Challenger 75'))
    n_ranked = 32 - n_unranked
    print(f"  ~{n_ranked} ranked players + ~{n_unranked} unranked (negligible)")
