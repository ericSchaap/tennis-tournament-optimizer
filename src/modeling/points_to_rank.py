"""
Tennis Tournament Optimizer - Points-to-Rank Mapping
=====================================================

Converts ranking points totals to approximate ATP rankings and vice versa.
Used by the seasonal optimizer to update a player's estimated ranking
during Monte Carlo simulation after accumulating points at each tournament.

Derived from ATP pro rankings data 2020-2026 (531,594 weekly observations).
Method: Median points at each rank position, smoothed with 5-rank rolling median.

Usage:
    from points_to_rank import PointsRankMapper
    mapper = PointsRankMapper()
    
    rank = mapper.points_to_rank(300)   # ~198
    points = mapper.rank_to_points(200) # ~297
    
    # During simulation: player gained 80 points at a Challenger
    new_points = old_points + 80
    new_rank = mapper.points_to_rank(new_points)
"""

import bisect

# Lookup table: rank -> typical points total
# Sampled from ATP rankings 2020-2026, smoothed
RANK_POINTS_TABLE = {
    1: 11015.0, 2: 8477.0, 3: 7265.0, 4: 6295.0, 5: 5050.0,
    6: 4770.0, 7: 4425.0, 8: 4220.0, 9: 3598.0, 10: 3235.0,
    11: 3125.0, 12: 3050.0, 13: 2900.0, 14: 2716.0, 15: 2581.0,
    16: 2485.0, 17: 2395.0, 18: 2295.0, 19: 2170.0, 20: 2050.0,
    22: 1920.0, 25: 1740.0, 27: 1655.0, 30: 1510.0,
    33: 1405.0, 35: 1340.0, 38: 1270.0, 40: 1200.0,
    43: 1145.0, 45: 1100.0, 48: 1052.0, 50: 1024.0,
    55: 940.0, 60: 873.0, 65: 830.0, 70: 800.0,
    75: 765.0, 80: 720.0, 85: 685.0, 90: 657.0,
    95: 634.0, 100: 617.0, 105: 570.0, 110: 545.0,
    115: 520.0, 120: 508.0, 125: 497.0, 130: 475.0,
    135: 458.0, 140: 445.0, 145: 425.0, 150: 407.0,
    155: 393.0, 160: 378.0, 165: 365.0, 170: 352.0,
    175: 340.0, 180: 327.0, 185: 317.0, 190: 310.0,
    195: 303.0, 200: 297.0, 210: 274.0, 220: 256.0,
    230: 241.0, 240: 232.0, 250: 224.0, 260: 212.0,
    270: 201.0, 280: 193.0, 290: 183.0, 300: 174.0,
    310: 167.0, 320: 159.0, 330: 152.0, 340: 146.0,
    350: 139.0, 360: 133.0, 370: 128.0, 380: 123.0,
    390: 119.0, 400: 115.0, 410: 110.0, 420: 105.0,
    430: 100.0, 440: 95.0, 450: 90.0, 460: 86.0,
    470: 82.0, 480: 79.0, 490: 77.0, 500: 74.0,
    520: 68.0, 540: 63.0, 560: 58.0, 580: 54.0,
    600: 51.0, 620: 47.0, 640: 44.0, 660: 41.0,
    680: 39.0, 700: 35.0, 720: 33.0, 740: 31.0,
    760: 29.0, 780: 28.0, 800: 24.0, 850: 21.0,
    900: 18.0, 950: 15.0, 1000: 12.0, 1050: 10.0,
    1100: 8.0, 1150: 7.0, 1200: 6.0, 1250: 5.0,
    1300: 4.0, 1400: 3.0, 1500: 2.0, 1700: 1.0,
    2000: 1.0,
}

# Entry thresholds: data-driven from first-round entrant analysis (2022-2025)
# reliable_rank = P75 of first-round entrants (rank that reliably gets DA)
# cutoff_rank = P95 of first-round entrants (rank where entry becomes very unlikely)
# Between reliable and cutoff: acceptance probability declines linearly
ENTRY_THRESHOLDS = {
    "Grand Slam": 104,              # Main draw direct acceptance
    "Grand Slam Qualifying": 250,    # Qualifying entry
    "Masters 1000": 100,             # P95 actual = 221, but DA cutoff ~80-100
    "ATP 500": 100,                  # P95 actual = 353, but DA cutoff ~80-100
    "ATP 250": 150,                  # P95 actual = 382, but DA cutoff ~100-150
    "Challenger 175": 400,
    "Challenger 125": 500,
    "Challenger 100": 600,
    "Challenger 80": 700,
    "Challenger 75": 700,
    "Challenger 50": 900,
    "Challenger": 700,               # Generic Challenger
    "ITF": 2000,                     # Essentially open entry
}

# Data-driven acceptance curves from first-round entrant analysis (2022-2025)
# Format: (reliable_rank, cutoff_rank)
# reliable_rank (P75): rank that reliably gets direct acceptance (~100%)
# cutoff_rank (P95): rank beyond which entry is very unlikely (<5%)
ACCEPTANCE_CURVES = {
    "Grand Slam (Men's)":   (97, 200),
    "Grand Slam (Women's)": (97, 200),
    "ATP 1000":             (77, 160),
    "WTA 1000":             (77, 160),
    "WTA 1000 (5)":         (77, 160),
    "ATP 500":              (87, 227),
    "WTA 500":              (87, 227),
    "ATP 250":              (125, 303),
    "WTA 250":              (125, 303),
    "WTA 125":              (200, 400),
    "Challenger 175":       (166, 333),
    "Challenger 125":       (294, 553),
    "Challenger 110":       (310, 600),
    "Challenger 100":       (336, 642),
    "Challenger 90":        (350, 680),
    "Challenger 80":        (366, 721),
    "Challenger 75":        (400, 779),
    "Challenger 50":        (536, 971),
    "Challengers":          (400, 700),
    "M25":                  (1500, 2500),
    "M15":                  (1800, 3000),
}


class PointsRankMapper:
    """
    Bidirectional mapping between ranking points and approximate ATP ranking.
    """
    
    def __init__(self, table=None):
        self.table = table or RANK_POINTS_TABLE
        
        # Pre-sort for fast lookup
        # For rank_to_points: sorted by rank (ascending)
        self._ranks = sorted(self.table.keys())
        self._points = [self.table[r] for r in self._ranks]
        
        # For points_to_rank: sorted by points (descending)
        self._points_desc = sorted(self.table.values(), reverse=True)
        self._ranks_by_pts = sorted(self.table.keys(), 
                                      key=lambda r: self.table[r], reverse=True)
    
    def rank_to_points(self, rank):
        """
        Given a ranking, return the typical points total.
        Interpolates between table entries.
        """
        if rank <= self._ranks[0]:
            return self._points[0]
        if rank >= self._ranks[-1]:
            return self._points[-1]
        
        # Find surrounding entries
        idx = bisect.bisect_left(self._ranks, rank)
        if self._ranks[idx] == rank:
            return self._points[idx]
        
        # Interpolate
        r_lo = self._ranks[idx - 1]
        r_hi = self._ranks[idx]
        p_lo = self.table[r_lo]
        p_hi = self.table[r_hi]
        
        frac = (rank - r_lo) / (r_hi - r_lo)
        return round(p_lo + frac * (p_hi - p_lo), 1)
    
    def points_to_rank(self, points):
        """
        Given a points total, return the approximate ranking.
        Interpolates between table entries.
        """
        if points >= self._points_desc[0]:
            return self._ranks_by_pts[0]  # rank 1
        if points <= self._points_desc[-1]:
            return self._ranks_by_pts[-1]  # lowest rank
        
        # Find where this points total falls (descending order)
        for i in range(len(self._points_desc) - 1):
            if self._points_desc[i] >= points >= self._points_desc[i + 1]:
                r_hi = self._ranks_by_pts[i]      # better rank (fewer number)
                r_lo = self._ranks_by_pts[i + 1]   # worse rank
                p_hi = self._points_desc[i]
                p_lo = self._points_desc[i + 1]
                
                if p_hi == p_lo:
                    return r_hi
                
                frac = (p_hi - points) / (p_hi - p_lo)
                return int(round(r_hi + frac * (r_lo - r_hi)))
        
        return self._ranks_by_pts[-1]
    
    def acceptance_probability(self, rank, category):
        """
        Return the probability (0-1) that a player with given rank
        gets accepted into a tournament of this category.
        
        Uses data-driven curves from first-round entrant analysis.
        Between reliable_rank and cutoff_rank: linear decline from 1.0 to 0.05.
        """
        cat = category.strip()
        
        # Try exact match first
        if cat in ACCEPTANCE_CURVES:
            reliable, cutoff = ACCEPTANCE_CURVES[cat]
        elif 'Challenger' in cat:
            # Match by prize level
            for level_str in ['175', '125', '110', '100', '90', '80', '75', '50']:
                key = f'Challenger {level_str}'
                if level_str in cat and key in ACCEPTANCE_CURVES:
                    reliable, cutoff = ACCEPTANCE_CURVES[key]
                    break
            else:
                reliable, cutoff = ACCEPTANCE_CURVES.get('Challengers', (400, 700))
        elif cat in ('M25', 'M15') or cat.startswith('W'):
            reliable, cutoff = ACCEPTANCE_CURVES.get(cat, (1500, 2500))
        elif 'ATP Finals' in cat or 'Year End' in cat:
            return 1.0 if rank <= 8 else 0.0
        else:
            # Unknown category — default permissive
            return 1.0 if rank <= 2000 else 0.0
        
        if rank <= reliable:
            return 1.0
        elif rank >= cutoff:
            return 0.05  # Wild card / alternate chance
        else:
            # Linear decline
            return 1.0 - 0.95 * (rank - reliable) / (cutoff - reliable)
    
    def can_enter(self, rank, category, min_probability=0.15):
        """
        Check if a player with given rank can realistically enter a
        tournament category. Returns True if acceptance probability
        exceeds min_probability (default 15%).
        """
        return self.acceptance_probability(rank, category) >= min_probability
    
    def simulate_ranking_change(self, current_rank, current_points, points_gained,
                                points_expiring=0):
        """
        Simulate what happens to ranking after gaining points.
        
        Note: This is approximate. Actual ranking depends on other players'
        results, which we can't predict. This gives the historical average
        ranking for the new points total.
        
        Args:
            current_rank: Current ranking
            current_points: Current points total
            points_gained: Points earned at a tournament
            points_expiring: Points dropping off from 52 weeks ago (0 if unknown)
        
        Returns:
            dict with new_points, new_rank, rank_change, unlocked tiers
        """
        new_points = current_points + points_gained - points_expiring
        new_points = max(0, new_points)
        new_rank = self.points_to_rank(new_points)
        
        # Check what new tiers are unlocked
        newly_unlocked = []
        for tier, threshold in sorted(ENTRY_THRESHOLDS.items(), 
                                        key=lambda x: x[1]):
            if current_rank > threshold >= new_rank:
                newly_unlocked.append(tier)
        
        return {
            "old_rank": current_rank,
            "old_points": current_points,
            "points_gained": points_gained,
            "points_expiring": points_expiring,
            "new_points": new_points,
            "new_rank": new_rank,
            "rank_change": current_rank - new_rank,  # positive = improvement
            "newly_unlocked": newly_unlocked,
        }


# =========================================================================
# DEMO
# =========================================================================
if __name__ == '__main__':
    mapper = PointsRankMapper()
    
    print("Points-to-Rank Mapping")
    print("=" * 55)
    
    print(f"\n{'Points':>8s}  {'Approx Rank':>12s}  {'Can Enter':>30s}")
    print("-" * 55)
    for pts in [8000, 5000, 3000, 2000, 1000, 500, 300, 200, 100, 50, 20, 10]:
        rank = mapper.points_to_rank(pts)
        tiers = [t for t, th in ENTRY_THRESHOLDS.items() if rank <= th]
        print(f"  {pts:>6.0f}  ->  rank {rank:>4d}     {', '.join(tiers[:3])}")
    
    print(f"\n\nRank-to-Points (reverse):")
    print("-" * 40)
    for rank in [1, 10, 50, 100, 200, 300, 500, 1000]:
        pts = mapper.rank_to_points(rank)
        print(f"  Rank {rank:>4d}  ->  ~{pts:.0f} points")
    
    # Simulate a player's progression
    print(f"\n\nSimulation: Rank 250 player winning a Challenger")
    print("-" * 55)
    result = mapper.simulate_ranking_change(
        current_rank=250, current_points=224, points_gained=80)
    print(f"  Before: rank {result['old_rank']}, {result['old_points']} points")
    print(f"  Gained: {result['points_gained']} points (Challenger title)")
    print(f"  After:  rank {result['new_rank']}, {result['new_points']} points")
    print(f"  Improvement: +{result['rank_change']} positions")
    if result['newly_unlocked']:
        print(f"  UNLOCKED: {', '.join(result['newly_unlocked'])}")
    
    # Chain of tournaments
    print(f"\n\nSimulation: Clay season progression")
    print("-" * 55)
    current_rank = 250
    current_points = 224
    
    season = [
        ("Challenger Lyon, Clay", 18),     # QF
        ("M25 Monastir, Clay", 6),          # QF
        ("Challenger Aix, Clay", 35),       # SF
        ("Challenger Prague, Clay", 5),     # R2
        ("M25 Tunis, Clay", 12),            # SF
        ("Challenger Rome, Clay", 80),      # Winner!
    ]
    
    for tournament, pts in season:
        result = mapper.simulate_ranking_change(current_rank, current_points, pts)
        unlock_str = f"  ** UNLOCKED: {', '.join(result['newly_unlocked'])} **" \
                     if result['newly_unlocked'] else ""
        print(f"  {tournament:<30s} +{pts:>3d} pts -> rank {result['new_rank']:>3d} "
              f"({result['rank_change']:>+3d}){unlock_str}")
        current_rank = result['new_rank']
        current_points = result['new_points']
    
    print(f"\n  Season total: {current_points - 224} points gained, "
          f"rank {250} -> {current_rank}")
