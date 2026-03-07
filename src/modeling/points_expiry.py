"""
Tennis Tournament Optimizer - Points Expiry Module
====================================================

Calculates week-by-week ranking points balance, including exact expiry
of points earned at specific tournaments. Points in tennis expire on
the 52-week anniversary of the tournament where they were earned.

Designed to work purely from user input — no database lookup required.

Three input modes:
  1. Full detail: user provides tournament + round reached (we look up points)
  2. Direct points: user provides tournament week + points earned
  3. No history: estimate flat expiry from total points (fallback)

Usage:
    from points_expiry import PointsExpiryTracker

    tracker = PointsExpiryTracker(current_total_points=224)

    # Mode 1: Add by tournament result
    tracker.add_tournament_result(week=19, category="Challenger 75", round_reached="QF")
    tracker.add_tournament_result(week=22, category="M25", round_reached="SF")

    # Mode 2: Add by direct points
    tracker.add_points(week=30, points=45, label="Challenger Bordeaux")

    # Get expiry schedule
    expiry = tracker.get_expiry_schedule()

    # Get points balance at any future week
    balance = tracker.get_balance_at_week(target_week=20, current_week=14)

    # Feed into optimizer
    weekly_expiry = tracker.get_weekly_expiry_for_window(start_week=14, end_week=24)
"""

import os
import sys

# Add modeling directory to path for tournament_economics import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from tournament_economics import get_points_table
except ImportError:
    get_points_table = None


# =========================================================================
# FALLBACK POINTS TABLE (in case tournament_economics is not available)
# =========================================================================
# Simplified: category -> round -> points
POINTS_FALLBACK = {
    "Grand Slam": {
        '1/128': 10, '1/64': 45, '1/32': 90, '1/16': 180,
        '1/8': 360, 'QF': 720, 'SF': 1200, 'F': 2000, 'W': 2000,
    },
    "ATP 1000": {
        '1/32': 10, '1/16': 45, '1/8': 90, 'QF': 180,
        'SF': 360, 'F': 600, 'W': 1000,
    },
    "ATP 500": {
        '1/16': 45, '1/8': 90, 'QF': 180, 'SF': 300, 'F': 500, 'W': 500,
    },
    "ATP 250": {
        '1/16': 20, '1/8': 45, 'QF': 90, 'SF': 150, 'F': 250, 'W': 250,
    },
    "Challenger 175": {
        '1/16': 8, '1/8': 15, 'QF': 35, 'SF': 60, 'F': 100, 'W': 175,
    },
    "Challenger 125": {
        '1/16': 5, '1/8': 10, 'QF': 25, 'SF': 45, 'F': 75, 'W': 125,
    },
    "Challenger 100": {
        '1/16': 5, '1/8': 8, 'QF': 18, 'SF': 35, 'F': 60, 'W': 100,
    },
    "Challenger 80": {
        '1/16': 3, '1/8': 6, 'QF': 15, 'SF': 30, 'F': 50, 'W': 80,
    },
    "Challenger 75": {
        '1/16': 3, '1/8': 6, 'QF': 12, 'SF': 25, 'F': 40, 'W': 65,
    },
    "Challenger 50": {
        '1/16': 3, '1/8': 6, 'QF': 12, 'SF': 25, 'F': 40, 'W': 65,
    },
    "M25": {
        '1/16': 1, '1/8': 3, 'QF': 6, 'SF': 12, 'F': 20, 'W': 25,
    },
    "M15": {
        '1/16': 1, '1/8': 1, 'QF': 2, 'SF': 4, 'F': 6, 'W': 10,
    },
}

# Map common user-facing category names to lookup keys
CATEGORY_ALIASES = {
    "Grand Slam (Men's)": "Grand Slam",
    "Grand Slam (Women's)": "Grand Slam",
    "Grand Slam": "Grand Slam",
    "ATP 1000": "ATP 1000",
    "WTA 1000": "ATP 1000",
    "ATP 500": "ATP 500",
    "WTA 500": "ATP 500",
    "ATP 250": "ATP 250",
    "WTA 250": "ATP 250",
    "Challenger 175": "Challenger 175",
    "Challenger 125": "Challenger 125",
    "Challenger 110": "Challenger 100",
    "Challenger 100": "Challenger 100",
    "Challenger 90": "Challenger 80",
    "Challenger 80": "Challenger 80",
    "Challenger 75": "Challenger 75",
    "Challenger 50": "Challenger 50",
    "Challengers": "Challenger 75",
    "M25": "M25",
    "M15": "M15",
}

# Round name normalization
ROUND_ALIASES = {
    'R128': '1/128', 'R64': '1/64', 'R32': '1/32', 'R16': '1/16',
    'R8': '1/8', 'r1': '1/16', 'r2': '1/8', 'r3': 'QF',
    'round of 128': '1/128', 'round of 64': '1/64',
    'round of 32': '1/32', 'round of 16': '1/16',
    'quarterfinal': 'QF', 'quarterfinals': 'QF',
    'semifinal': 'SF', 'semifinals': 'SF',
    'final': 'F', 'finals': 'F',
    'winner': 'W', 'won': 'W', 'title': 'W',
}


def lookup_points(category, round_reached):
    """
    Look up ranking points for a given category and round reached.
    
    Args:
        category: Tournament category (e.g., "Challenger 75", "M25")
        round_reached: Round reached (e.g., "QF", "SF", "W", "1/16")
    
    Returns:
        int: Points earned, or 0 if lookup fails
    """
    # Normalize round
    round_norm = ROUND_ALIASES.get(round_reached.lower().strip(), round_reached.strip())
    
    # Try tournament_economics module first
    if get_points_table is not None:
        table = get_points_table(category)
        if table and round_norm in table:
            return table[round_norm]
        # Winner special case: if user says "W" but table uses "F" for winner
        if round_norm == 'W' and 'W' not in (table or {}) and 'F' in (table or {}):
            return table['F']
    
    # Fallback to embedded table
    cat_key = CATEGORY_ALIASES.get(category, category)
    
    # Try fuzzy match on category
    if cat_key not in POINTS_FALLBACK:
        for alias, key in CATEGORY_ALIASES.items():
            if alias.lower() in category.lower():
                cat_key = key
                break
    
    table = POINTS_FALLBACK.get(cat_key, {})
    points = table.get(round_norm, 0)
    
    # Winner fallback
    if points == 0 and round_norm == 'W' and 'F' in table:
        points = table['F']
    
    return points


class PointsExpiryTracker:
    """
    Tracks ranking points and their expiry schedule.
    
    Points in tennis expire exactly 52 weeks after the tournament
    where they were earned. This tracker maintains a week-by-week
    ledger of points earned and their expiry dates.
    """
    
    def __init__(self, current_total_points=0):
        """
        Args:
            current_total_points: Player's current ranking points total.
                Used for fallback estimation when individual tournament
                history is incomplete.
        """
        self.current_total_points = current_total_points
        self.entries = []  # List of {week, points, category, round, label}
    
    def add_tournament_result(self, week, category, round_reached, label=None):
        """
        Add a tournament result. Points are looked up automatically.
        
        Args:
            week: Calendar week the tournament was played (1-52)
            category: Tournament category (e.g., "Challenger 75")
            round_reached: Deepest round reached (e.g., "QF", "W")
            label: Optional tournament name for display
        """
        points = lookup_points(category, round_reached)
        
        self.entries.append({
            'week': week,
            'points': points,
            'category': category,
            'round': round_reached,
            'label': label or f"{category} (wk {week})",
        })
        
        return points  # Return so the user can verify
    
    def add_points(self, week, points, label=None):
        """
        Add points directly (when the user knows the exact amount).
        
        Args:
            week: Calendar week the points were earned
            points: Number of ranking points
            label: Optional description
        """
        self.entries.append({
            'week': week,
            'points': points,
            'category': 'manual',
            'round': 'manual',
            'label': label or f"{points} pts (wk {week})",
        })
    
    def get_tracked_total(self):
        """Sum of all individually tracked point entries."""
        return sum(e['points'] for e in self.entries)
    
    def get_untracked_points(self):
        """
        Points in the total that aren't accounted for by individual entries.
        These get the flat-average expiry treatment.
        """
        return max(0, self.current_total_points - self.get_tracked_total())
    
    def get_expiry_schedule(self):
        """
        Get the full expiry schedule: which points expire in which week.
        
        Points expire 52 weeks after they were earned. For tracked
        tournaments, this is exact. For untracked points, they're
        spread evenly across the year.
        
        Returns:
            dict: {expiry_week: [list of expiring entries]}
        """
        schedule = {}
        
        # Tracked entries: expire exactly 52 weeks later
        for entry in self.entries:
            expiry_week = entry['week']  # Same week next year = 52 weeks later
            if expiry_week not in schedule:
                schedule[expiry_week] = []
            schedule[expiry_week].append({
                'points': entry['points'],
                'label': entry['label'],
                'source': 'tracked',
            })
        
        # Untracked points: spread evenly across 44 active weeks
        untracked = self.get_untracked_points()
        if untracked > 0:
            weekly_untracked = untracked / 44.0
            for week in range(1, 53):
                if week not in schedule:
                    schedule[week] = []
                schedule[week].append({
                    'points': round(weekly_untracked, 1),
                    'label': 'estimated (untracked)',
                    'source': 'estimated',
                })
        
        return schedule
    
    def get_weekly_expiry_for_window(self, start_week, end_week):
        """
        Get points expiring per week within a planning window.
        
        This is the primary interface for the optimizer. Returns a dict
        mapping each week in the window to the points expiring that week.
        
        Args:
            start_week: First week of planning window
            end_week: Last week of planning window
        
        Returns:
            dict: {week: total_points_expiring}
        """
        schedule = self.get_expiry_schedule()
        weekly = {}
        
        for week in range(start_week, end_week + 1):
            entries = schedule.get(week, [])
            weekly[week] = sum(e['points'] for e in entries)
        
        return weekly
    
    def get_balance_at_week(self, target_week, current_week):
        """
        Project what the points balance will be at a future week,
        accounting only for expiry (not new points earned).
        
        Args:
            target_week: Week to project balance for
            current_week: Current week number
        
        Returns:
            float: Projected points balance
        """
        if target_week <= current_week:
            return float(self.current_total_points)
        
        schedule = self.get_expiry_schedule()
        total_expiring = 0
        
        for week in range(current_week + 1, target_week + 1):
            entries = schedule.get(week, [])
            total_expiring += sum(e['points'] for e in entries)
        
        return max(0, self.current_total_points - total_expiring)
    
    def get_defense_priorities(self, start_week, end_week, min_points=5):
        """
        Identify weeks where significant points are expiring.
        These are weeks where the player should prioritise playing
        a strong tournament to offset the loss.
        
        Args:
            start_week: Start of planning window
            end_week: End of planning window
            min_points: Minimum points to flag as significant
        
        Returns:
            list of dicts with week, points_expiring, entries, sorted by
            points descending (most urgent first)
        """
        schedule = self.get_expiry_schedule()
        priorities = []
        
        for week in range(start_week, end_week + 1):
            entries = schedule.get(week, [])
            total = sum(e['points'] for e in entries)
            if total >= min_points:
                priorities.append({
                    'week': week,
                    'points_expiring': total,
                    'entries': entries,
                })
        
        priorities.sort(key=lambda x: -x['points_expiring'])
        return priorities
    
    def summary(self):
        """Print a human-readable summary of the points situation."""
        print(f"Points Expiry Summary")
        print(f"{'=' * 55}")
        print(f"  Current total: {self.current_total_points} points")
        print(f"  Tracked:       {self.get_tracked_total()} points "
              f"({len(self.entries)} tournaments)")
        print(f"  Untracked:     {self.get_untracked_points()} points "
              f"(estimated flat expiry)")
        
        if self.entries:
            print(f"\n  Tracked tournaments:")
            for e in sorted(self.entries, key=lambda x: x['week']):
                print(f"    Wk{e['week']:>2d}: {e['label']:<35s} "
                      f"{e['round']:>5s} -> {e['points']:>3d} pts "
                      f"(expires wk {e['week']})")
        
        print(f"\n  Heaviest expiry weeks:")
        schedule = self.get_expiry_schedule()
        week_totals = [(w, sum(e['points'] for e in entries))
                       for w, entries in schedule.items()]
        week_totals.sort(key=lambda x: -x[1])
        for week, total in week_totals[:5]:
            if total > 0:
                print(f"    Week {week:>2d}: {total:>5.0f} pts expiring")


# =========================================================================
# DEMO
# =========================================================================
if __name__ == '__main__':
    print("Points Expiry Module - Demo")
    print("=" * 55)
    
    # Scenario: Rank ~250 player with 224 points
    # They played these tournaments in the past year
    tracker = PointsExpiryTracker(current_total_points=224)
    
    # Add their tournament history
    history = [
        (3,  "Challenger 75",  "1/16", "Challenger Canberra"),
        (7,  "Challenger 100", "QF",   "Challenger Dallas"),
        (10, "M25",            "SF",   "M25 Antalya"),
        (14, "Challenger 75",  "QF",   "Challenger Barletta"),
        (17, "Challenger 75",  "1/8",  "Challenger Rome"),
        (19, "Challenger 100", "SF",   "Challenger Lyon"),
        (22, "M25",            "W",    "M25 Monastir"),
        (25, "Challenger 75",  "1/16", "Challenger Wimbledon Qualifying"),
        (30, "Challenger 75",  "QF",   "Challenger Salzburg"),
        (35, "Challenger 100", "1/8",  "Challenger Rennes"),
        (40, "M25",            "QF",   "M25 Hammamet"),
        (45, "Challenger 75",  "SF",   "Challenger Helsinki"),
    ]
    
    print("\nAdding tournament history:")
    for week, cat, rnd, name in history:
        pts = tracker.add_tournament_result(week, cat, rnd, name)
        print(f"  Wk{week:>2d}: {name:<30s} {rnd:>5s} = {pts:>3d} pts")
    
    # Summary
    print()
    tracker.summary()
    
    # Planning window analysis
    print(f"\n\nPlanning Window: Weeks 14-24 (clay season)")
    print(f"-" * 55)
    
    weekly = tracker.get_weekly_expiry_for_window(14, 24)
    for week, pts in sorted(weekly.items()):
        bar = "█" * int(pts / 2)
        print(f"  Week {week:>2d}: {pts:>5.1f} pts expiring  {bar}")
    
    total_window_expiry = sum(weekly.values())
    print(f"\n  Total expiring in window: {total_window_expiry:.0f} pts")
    
    # Defense priorities
    print(f"\n  Defense priorities:")
    priorities = tracker.get_defense_priorities(14, 24)
    for p in priorities:
        entries_str = ", ".join(e['label'] for e in p['entries'] if e['source'] == 'tracked')
        if entries_str:
            print(f"    Week {p['week']:>2d}: {p['points_expiring']:>5.1f} pts — {entries_str}")
    
    # Projected balance
    print(f"\n  Projected balance (no new points):")
    for week in [14, 16, 18, 20, 22, 24]:
        balance = tracker.get_balance_at_week(week, current_week=13)
        print(f"    Week {week:>2d}: {balance:.0f} pts remaining")
    
    # Show how to feed into optimizer
    print(f"\n\n{'=' * 55}")
    print("Integration with optimizer:")
    print(f"{'=' * 55}")
    print(f"""
    from points_expiry import PointsExpiryTracker
    
    tracker = PointsExpiryTracker(current_total_points=224)
    tracker.add_tournament_result(19, "Challenger 100", "SF", "Lyon")
    tracker.add_tournament_result(22, "M25", "W", "Monastir")
    
    # Pass to optimizer's simulation loop:
    weekly_expiry = tracker.get_weekly_expiry_for_window(14, 24)
    
    # In each simulation step, instead of:
    #   points_expiring = player_points / 44.0 * weeks_elapsed
    # Use:
    #   points_expiring = sum(weekly_expiry[w] for w in range(last_week+1, current_week+1))
    """)
