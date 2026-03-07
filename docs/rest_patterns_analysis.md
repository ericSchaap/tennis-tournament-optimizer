# Tennis Tournament Optimizer — Rest & Scheduling Patterns

**Source:** 340,912 player-tournament entries from ATP pro-level data (2015–2026), 7,582 unique players.

---

## Key Findings

### 1. The Tennis Calendar Runs on a Weekly Rhythm

The dominant gap between tournaments is **1 day** — 58% of all between-tournament gaps. This reflects the standard weekly cycle: tournaments run Monday–Sunday, and the next starts the following Monday. The second most common gap is **8 days** (15%), representing one week off between events. After that, **15 days** (8%) and **22 days** (4%) show two- and three-week breaks.

In practical terms, **60% of tournament transitions are back-to-back** (0–1 day gap), meaning players overwhelmingly play consecutive weeks when active.

### 2. Top Players Take More Rest

| Rank Level | Median Gap | Mean Gap | Back-to-Back % | Tournaments/Year |
|------------|-----------|----------|----------------|-----------------|
| Top 10     | 8 days    | 8.1 days | 36.8%          | 16 (median)     |
| Top 30     | 1 day     | 5.7 days | 52.4%          | 21              |
| Top 50     | 1 day     | 4.7 days | 61.7%          | 22              |
| 51–100     | 1 day     | 4.7 days | 63.4%          | 22              |
| 101–200    | 1 day     | 5.5 days | 57.3%          | 20              |
| 201–500    | 1 day     | 5.8 days | 62.3%          | 17              |
| 500+       | 1 day     | 8.0 days | 59.8%          | 7               |

Top 10 players play **fewer tournaments** (16/year vs 22 for the 51–100 bracket) but take **longer breaks** between them (median 8 days vs 1 day). This reflects their ability to be selective — they play only the most valuable events and rest between them.

Players in the 51–200 range are the most active: ~20–22 tournaments per year, with 57–63% played back-to-back.

The 500+ group plays fewer tournaments (median 7) because many are part-time or early-career players building up.

### 3. Grand Slams Demand More Recovery

| Tournament Tier      | Median Gap After | Mean Gap After | 25th–75th Percentile |
|---------------------|-----------------|---------------|---------------------|
| Grand Slam          | 8 days          | 10.1 days     | 3–15 days           |
| ATP 1000            | 1 day           | 5.0 days      | 1–8 days            |
| ATP 500             | 1 day           | 4.2 days      | 1–8 days            |
| ATP 250             | 1 day           | 4.3 days      | 1–7 days            |
| Challenger          | 1 day           | 6.0 days      | 1–8 days            |
| ITF M25/M15         | 1 day           | 7.8 days      | 1–8 days            |

After Grand Slams (best-of-5, two-week events), players take a median **8 days off** with a long tail extending to 15+ days. After all other tournament types, the median gap is just 1 day — straight into the next event.

The ITF level shows a slightly higher mean gap (7.8 days) than Challengers (6.0 days), likely because lower-ranked players have more variable schedules and travel between less conveniently located events.

### 4. Season Structure

| Rank Level | Median Season Length | Active Weeks |
|------------|---------------------|-------------|
| Top 10     | 43 weeks            | ~16 playing |
| Top 50     | 43 weeks            | ~22 playing |
| 101–200    | 44 weeks            | ~20 playing |
| 201–500    | 43 weeks            | ~17 playing |
| 500+       | 38 weeks            | ~7 playing  |

Most pro players have a **43-week season** from first to last tournament. For a rank 101–200 player (the optimizer's target user), this means roughly 44 weeks of season with 20 playing weeks — leaving about 24 weeks of rest, travel, and training scattered throughout.

---

## Implications for the Optimizer

**Default rest constraint:** Minimum 1 day between tournament end and next start (the data shows this is how 60% of transitions work). For the optimizer, this means consecutive-week tournaments are feasible and common.

**Post-Grand-Slam rest:** Build in a minimum 7-day gap after any Grand Slam. The data strongly supports this — even aggressive schedulers take a week off.

**Rank-dependent scheduling density:** A rank 100–200 player should plan for 20–25 tournaments per year. The optimizer should warn if a plan exceeds 28 tournaments or has more than 4 consecutive back-to-back weeks.

**Fatigue modeling (future enhancement):** The data suggests diminishing returns from consecutive weeks of play. A future version could model win probability as declining after 3+ back-to-back tournaments, nudging the optimizer toward strategic rest weeks.
