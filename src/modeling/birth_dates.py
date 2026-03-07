"""
Tennis Tournament Optimizer - Player Birth Date Lookup
=======================================================

Provides precise player ages at match time by combining two data sources:
  1. birth_date from rankings data (ISO format, 91% coverage)
  2. birth_year from player profiles (93% coverage, less precise)

Prefers birth_date for exact age calculation. Falls back to birth_year
(assumes July 1 as midpoint) when full date is unavailable.

Usage in the pipeline:
    from birth_dates import BirthDateLookup

    lookup = BirthDateLookup()
    lookup.load(rankings_path, profiles_path)

    # Single lookup
    age = lookup.age_at_date(player_id=73531, match_date='2024-05-15')

    # Vectorized for DataFrame
    df['player_age'] = lookup.compute_ages(df, 'player_id', 'start_date_parsed')
    df['opponent_age'] = lookup.compute_ages(df, 'opponent_id', 'start_date_parsed')
"""

import pandas as pd
import numpy as np
from datetime import datetime


class BirthDateLookup:
    """
    Efficient lookup of player birth dates from multiple sources.
    """

    def __init__(self):
        self.birth_dates = {}  # player_id -> datetime (precise)
        self.birth_years = {}  # player_id -> int (fallback)

    def load(self, rankings_path, profiles_path):
        """
        Load birth date data from rankings and profiles files.
        Handles .gz files transparently.

        Args:
            rankings_path: Path to weekly rankings CSV (.csv or .csv.gz)
            profiles_path: Path to player profiles CSV (.csv or .csv.gz)
        """
        # Source 1: birth_date from rankings (precise)
        rankings = pd.read_csv(rankings_path,
                               usecols=['player_id', 'birth_date'],
                               low_memory=False)
        birth_dates = rankings.dropna(subset=['birth_date']).drop_duplicates('player_id')
        birth_dates['birth_date_parsed'] = pd.to_datetime(
            birth_dates['birth_date'], errors='coerce')
        valid = birth_dates[birth_dates['birth_date_parsed'].notna()]

        for _, row in valid.iterrows():
            self.birth_dates[row['player_id']] = row['birth_date_parsed']

        # Source 2: birth_year from profiles (fallback)
        profiles = pd.read_csv(profiles_path,
                               usecols=['player_id', 'birth_year'],
                               low_memory=False)
        birth_years = profiles.dropna(subset=['birth_year'])
        for _, row in birth_years.iterrows():
            pid = row['player_id']
            if pid not in self.birth_dates:  # Only use as fallback
                self.birth_years[pid] = int(row['birth_year'])

        n_precise = len(self.birth_dates)
        n_fallback = len(self.birth_years)
        print(f"    Birth dates loaded: {n_precise:,} precise, "
              f"{n_fallback:,} year-only fallback, "
              f"{n_precise + n_fallback:,} total")

    def get_birth_date(self, player_id):
        """
        Get a player's birth date.

        Returns:
            datetime if precise date is available,
            datetime(year, 7, 1) if only year is available,
            None if no data
        """
        if player_id in self.birth_dates:
            return self.birth_dates[player_id]
        elif player_id in self.birth_years:
            return datetime(self.birth_years[player_id], 7, 1)
        else:
            return None

    def age_at_date(self, player_id, match_date):
        """
        Calculate a player's age at a specific date.

        Args:
            player_id: Player identifier
            match_date: Date string (ISO format) or datetime

        Returns:
            float: Age in years (with decimal), or NaN if no birth data
        """
        birth = self.get_birth_date(player_id)
        if birth is None:
            return float('nan')

        if isinstance(match_date, str):
            match_date = pd.to_datetime(match_date)

        if pd.isna(match_date):
            return float('nan')

        delta = match_date - birth
        return round(delta.days / 365.25, 1)

    def compute_ages(self, df, player_id_col, date_col):
        """
        Vectorized age computation for a DataFrame.

        Args:
            df: DataFrame with player IDs and match dates
            player_id_col: Column name for player ID
            date_col: Column name for match date

        Returns:
            Series of ages (float, with NaN for missing)
        """
        dates = pd.to_datetime(df[date_col], errors='coerce')
        ages = np.full(len(df), np.nan)

        for idx in range(len(df)):
            pid = df.iloc[idx][player_id_col]
            mdate = dates.iloc[idx]
            if pd.notna(mdate):
                birth = self.get_birth_date(pid)
                if birth is not None:
                    ages[idx] = round((mdate - birth).days / 365.25, 1)

        return pd.Series(ages, index=df.index)

    def compute_ages_fast(self, df, player_id_col, date_col):
        """
        Faster vectorized age computation using merge.
        Preferred for large DataFrames.

        Args:
            df: DataFrame
            player_id_col: Column name for player ID
            date_col: Column name for match date (must be datetime)

        Returns:
            Series of ages
        """
        # Build lookup DataFrame
        records = []
        for pid, bdate in self.birth_dates.items():
            records.append({'_pid': pid, '_birth': bdate})
        for pid, byear in self.birth_years.items():
            records.append({'_pid': pid, '_birth': datetime(byear, 7, 1)})

        if not records:
            return pd.Series(np.nan, index=df.index)

        lookup_df = pd.DataFrame(records)
        lookup_df['_birth'] = pd.to_datetime(lookup_df['_birth'])

        # Merge
        merged = df[[player_id_col, date_col]].copy()
        merged.columns = ['_pid', '_mdate']
        merged['_mdate'] = pd.to_datetime(merged['_mdate'], errors='coerce')
        merged = merged.merge(lookup_df, on='_pid', how='left')

        # Calculate age
        delta = merged['_mdate'] - merged['_birth']
        ages = (delta.dt.days / 365.25).round(1)

        return ages


# =========================================================================
# DEMO
# =========================================================================
if __name__ == '__main__':
    import os

    print("Birth Date Lookup - Demo")
    print("=" * 50)

    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    rankings_path = os.path.join(base, 'data', 'raw', 'atp',
                                 'atp_all_weekly_rankings.csv.gz')
    profiles_path = os.path.join(base, 'data', 'raw', 'atp',
                                 'atp_player_profiles.csv.gz')

    if not os.path.exists(rankings_path):
        print("  Data files not found — skipping demo.")
    else:
        lookup = BirthDateLookup()
        lookup.load(rankings_path, profiles_path)

        # Test a few players
        import pandas as pd
        df = pd.read_csv(os.path.join(base, 'data', 'processed',
                                       'atp_clean_both_ranked.csv'),
                         usecols=['player_id', 'opponent_name',
                                  'start_date_parsed'],
                         nrows=10)

        print(f"\nSample age lookups:")
        for _, row in df.iterrows():
            age = lookup.age_at_date(row['player_id'], row['start_date_parsed'])
            birth = lookup.get_birth_date(row['player_id'])
            source = 'precise' if row['player_id'] in lookup.birth_dates else 'year-only'
            print(f"  Player {row['player_id']}: born {birth}, "
                  f"age {age} at match ({source})")
