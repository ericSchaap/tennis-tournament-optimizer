"""
Tennis Tournament Optimizer - Travel Cost Model
================================================

Simple three-tier travel cost model:
  - National: tournament in player's home country
  - International: tournament on the same continent
  - Intercontinental: tournament on a different continent

Costs represent approximate total expenses (flights + accommodation + meals)
for a one-week tournament trip.

Usage:
    from travel_costs import TravelCostModel
    
    travel = TravelCostModel(player_country='FRA')
    cost = travel.estimate_cost('ESP')  # International (Europe)
    tier = travel.get_tier('JPN')       # Intercontinental
"""

# ==============================================================================
# COUNTRY TO CONTINENT MAPPING
# ==============================================================================

# All 90 country codes that appear in the Coretennis data
COUNTRY_CONTINENT = {
    # Europe
    'ALB': 'Europe', 'AND': 'Europe', 'ARM': 'Europe', 'AUT': 'Europe',
    'AZE': 'Europe', 'BEL': 'Europe', 'BIH': 'Europe', 'BLR': 'Europe',
    'BUL': 'Europe', 'CRO': 'Europe', 'CYP': 'Europe', 'CZE': 'Europe',
    'DEN': 'Europe', 'ESP': 'Europe', 'EST': 'Europe', 'FIN': 'Europe',
    'FRA': 'Europe', 'GBR': 'Europe', 'GEO': 'Europe', 'GER': 'Europe',
    'GRE': 'Europe', 'HUN': 'Europe', 'IRL': 'Europe', 'ISR': 'Europe',
    'ITA': 'Europe', 'KOS': 'Europe', 'LAT': 'Europe', 'LIT': 'Europe',
    'LUX': 'Europe', 'MDA': 'Europe', 'MKD': 'Europe', 'MLT': 'Europe',
    'MNE': 'Europe', 'MON': 'Europe', 'NED': 'Europe', 'NOR': 'Europe',
    'POL': 'Europe', 'POR': 'Europe', 'ROU': 'Europe', 'RUS': 'Europe',
    'SLO': 'Europe', 'SRB': 'Europe', 'SUI': 'Europe', 'SVK': 'Europe',
    'SWE': 'Europe', 'TUR': 'Europe', 'UKR': 'Europe',
    
    # North America
    'CAN': 'North America', 'USA': 'North America', 'MEX': 'North America',
    'DOM': 'North America', 'GUA': 'North America', 'CRC': 'North America',
    'JAM': 'North America', 'TTO': 'North America', 'PUR': 'North America',
    'CUB': 'North America', 'BAH': 'North America',
    
    # South America
    'ARG': 'South America', 'BOL': 'South America', 'BRA': 'South America',
    'CHI': 'South America', 'COL': 'South America', 'ECU': 'South America',
    'PAR': 'South America', 'PER': 'South America', 'URU': 'South America',
    'VEN': 'South America',
    
    # Asia
    'BRN': 'Asia', 'CHN': 'Asia', 'HKG': 'Asia', 'IND': 'Asia',
    'INA': 'Asia', 'JPN': 'Asia', 'KAZ': 'Asia', 'KOR': 'Asia',
    'KGZ': 'Asia', 'MAS': 'Asia', 'PHI': 'Asia', 'QAT': 'Asia',
    'SGP': 'Asia', 'SRI': 'Asia', 'THA': 'Asia', 'TPE': 'Asia',
    'UAE': 'Asia', 'UZB': 'Asia', 'VIE': 'Asia',
    
    # Africa
    'ANG': 'Africa', 'CIV': 'Africa', 'EGY': 'Africa', 'KEN': 'Africa',
    'MAR': 'Africa', 'NGR': 'Africa', 'RSA': 'Africa', 'TUN': 'Africa',
    'UGA': 'Africa',
    
    # Oceania
    'AUS': 'Oceania', 'NZL': 'Oceania',
}

# North Africa (TUN, EGY, MAR) is geographically close to Europe
# so we treat it as "international" from Europe, not "intercontinental"
ADJACENT_REGIONS = {
    'Europe': ['Africa'],       # North Africa is close to Southern Europe
    'Africa': ['Europe'],
    'North America': ['South America'],
    'South America': ['North America'],
}


# ==============================================================================
# COST ESTIMATES (USD)
# ==============================================================================

# Total trip cost per tier (flights + hotel 5 nights + meals + local transport)
TRAVEL_COSTS = {
    'national': 800,            # Domestic flight/train + hotel
    'international': 1500,      # Short-haul flight + hotel
    'intercontinental': 3000,   # Long-haul flight + hotel + jet lag recovery
}

# Per-tier adjustments for expensive/cheap regions
REGION_COST_MULTIPLIERS = {
    'Europe': 1.0,
    'North America': 1.1,
    'Oceania': 1.2,
    'Asia': 0.85,
    'South America': 0.8,
    'Africa': 0.75,
}


class TravelCostModel:
    """
    Estimates travel costs based on player home country and tournament country.
    """
    
    def __init__(self, player_country='FRA'):
        self.player_country = player_country.upper()
        self.player_continent = COUNTRY_CONTINENT.get(self.player_country, 'Europe')
    
    def get_tier(self, tournament_country):
        """
        Determine travel tier: national, international, or intercontinental.
        """
        if not tournament_country or not isinstance(tournament_country, str):
            return 'international'  # Default for missing data
        tournament_country = tournament_country.upper()
        
        # Same country
        if tournament_country == self.player_country:
            return 'national'
        
        tournament_continent = COUNTRY_CONTINENT.get(tournament_country, 'Unknown')
        
        # Same continent
        if tournament_continent == self.player_continent:
            return 'international'
        
        # Adjacent regions (e.g., Europe <-> North Africa)
        adjacent = ADJACENT_REGIONS.get(self.player_continent, [])
        if tournament_continent in adjacent:
            return 'international'
        
        return 'intercontinental'
    
    def estimate_cost(self, tournament_country):
        """
        Estimate total trip cost in USD.
        """
        if not tournament_country or not isinstance(tournament_country, str):
            tournament_country = 'UNK'
        tier = self.get_tier(tournament_country)
        base_cost = TRAVEL_COSTS[tier]
        
        # Adjust for destination cost of living
        dest_continent = COUNTRY_CONTINENT.get(tournament_country.upper(), 'Europe')
        multiplier = REGION_COST_MULTIPLIERS.get(dest_continent, 1.0)
        
        return round(base_cost * multiplier)
    
    def get_schedule_travel_info(self, schedule):
        """
        Analyze travel for a full schedule.
        
        Args:
            schedule: list of (week, tournament_dict) tuples
        
        Returns:
            dict with total cost, per-tournament costs, tier breakdown
        """
        total_cost = 0
        details = []
        tier_counts = {'national': 0, 'international': 0, 'intercontinental': 0}
        
        prev_country = self.player_country
        
        for week, tournament in schedule:
            tourn_country = tournament.get('country', 'UNK')
            if not isinstance(tourn_country, str):
                tourn_country = 'UNK'
            tier = self.get_tier(tourn_country)
            cost = self.estimate_cost(tourn_country)
            
            # Bonus: consecutive tournaments in same country/region are cheaper
            if tourn_country == prev_country:
                cost = int(cost * 0.6)  # Already there, just hotel
            
            total_cost += cost
            tier_counts[tier] += 1
            details.append({
                'week': week,
                'tournament': tournament.get('tournament_name', '?'),
                'country': tourn_country,
                'tier': tier,
                'cost': cost,
            })
            prev_country = tourn_country
        
        return {
            'total_cost': total_cost,
            'per_tournament': details,
            'tier_breakdown': tier_counts,
            'avg_cost_per_tournament': round(total_cost / max(len(schedule), 1)),
        }


# ==============================================================================
# DEMO
# ==============================================================================
if __name__ == '__main__':
    print("Travel Cost Model")
    print("=" * 60)
    
    # French player
    model = TravelCostModel(player_country='FRA')
    
    print(f"\nPlayer country: France (FRA)")
    print(f"Player continent: {model.player_continent}\n")
    
    test_countries = [
        ('FRA', 'Lyon Challenger'),
        ('ESP', 'Barcelona Open'),
        ('ITA', 'Rome Masters'),
        ('GBR', 'Wimbledon'),
        ('TUN', 'M25 Monastir'),
        ('USA', 'US Open'),
        ('AUS', 'Australian Open'),
        ('CHN', 'Shanghai Masters'),
        ('ARG', 'Buenos Aires'),
        ('IND', 'Bengaluru Challenger'),
    ]
    
    print(f"{'Tournament':<25s} {'Country':>8s} {'Tier':<18s} {'Cost':>8s}")
    print("-" * 65)
    for country, name in test_countries:
        tier = model.get_tier(country)
        cost = model.estimate_cost(country)
        print(f"  {name:<23s} {country:>8s} {tier:<18s} ${cost:>6,}")
    
    # Schedule cost analysis
    print(f"\n\nSchedule Travel Analysis:")
    print("-" * 60)
    schedule = [
        (14, {'tournament_name': 'Challenger Marbella', 'country': 'ESP'}),
        (15, {'tournament_name': 'Challenger Bordeaux', 'country': 'FRA'}),
        (16, {'tournament_name': 'Challenger Aix-en-Provence', 'country': 'FRA'}),
        (17, {'tournament_name': 'Challenger Francavilla', 'country': 'ITA'}),
        (19, {'tournament_name': 'Challenger Lyon', 'country': 'FRA'}),
        (20, {'tournament_name': 'Challenger Prague', 'country': 'CZE'}),
        (21, {'tournament_name': 'Challenger Geneva', 'country': 'SUI'}),
    ]
    
    info = model.get_schedule_travel_info(schedule)
    for d in info['per_tournament']:
        print(f"  W{d['week']:>2d}: {d['tournament']:<30s} {d['country']} "
              f"({d['tier']:<15s}) ${d['cost']:>5,}")
    
    print(f"\n  Total travel cost: ${info['total_cost']:,}")
    print(f"  Average per tournament: ${info['avg_cost_per_tournament']:,}")
    print(f"  Tiers: {info['tier_breakdown']}")
    
    # Compare: same schedule for an Argentine player
    print(f"\n\nSame schedule for Argentine player:")
    print("-" * 60)
    model_arg = TravelCostModel(player_country='ARG')
    info_arg = model_arg.get_schedule_travel_info(schedule)
    for d in info_arg['per_tournament']:
        print(f"  W{d['week']:>2d}: {d['tournament']:<30s} {d['country']} "
              f"({d['tier']:<15s}) ${d['cost']:>5,}")
    print(f"\n  Total travel cost: ${info_arg['total_cost']:,}")
    print(f"  Difference vs French player: +${info_arg['total_cost'] - info['total_cost']:,}")
