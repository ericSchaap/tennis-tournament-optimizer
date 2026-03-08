# Seedr

> A competition portfolio optimizer that helps resource-constrained athletes make data-driven decisions about which events to enter — maximizing competitive growth while staying financially sustainable. Tennis is the MVP; the framework extends to any sport with open-entry events, variable costs, and measurable returns.

## The Problem

Even world-class tennis players outside the top 100 struggle to compete profitably. Lower-ranked professionals and ambitious amateurs face hundreds of potential tournaments each year with no systematic way to answer: *"Which tournaments should I play to develop my career without going broke?"*

Seedr combines historical match data with Monte Carlo simulation to estimate round-reach probabilities for any player at any tournament, then layers in economics (prize money, entry fees, travel costs) and scheduling constraints to produce optimized seasonal tournament portfolios.

## How It Works

1. **Data Pipeline** — Scraped historical match and ranking data from Coretennis.net, cleaned and joined across ATP/WTA tours
2. **Win Probability Model** — Surface-adjusted, rating-differential-based model calibrated on 100k+ historical matches
3. **Monte Carlo Simulation** — Simulates full tournament draws to produce round-reach probability distributions
4. **Tournament Economics** — Entry fees, prize money by round, travel cost estimation, and net ROI calculation
5. **Seasonal Optimizer** — Budget-constrained schedule optimization across a tournament window, accounting for rest patterns, travel, ranking point defense, and financial targets

## Repository Structure

```
seedr/
├── docs/
│   ├── project-management/       # Charter, roadmap
│   │   ├── PROJECT_CHARTER_v2.docx
│   │   └── PRODUCT_ROADMAP.docx
│   ├── technical/                # Architecture docs
│   ├── MVP_Design_Document.docx
│   ├── validation_report_v2.md
│   └── backtest_validation_report.md
├── data/
│   ├── raw/                      # Scraped ATP & WTA data (compressed)
│   └── processed/                # Cleaned, analysis-ready datasets
├── models/                       # Trained model artifacts & lookup tables
│   ├── field_profiles.json
│   ├── category_field_fallbacks.json
│   └── tournament_name_to_key.json
├── src/
│   ├── modeling/                 # Core engine (Python)
│   │   ├── 00_unified_pipeline.py
│   │   ├── win_probability.py
│   │   ├── field_prediction.py
│   │   ├── tournament_economics.py
│   │   ├── scheduling_constraints.py
│   │   ├── points_to_rank.py
│   │   ├── points_expiry.py
│   │   ├── travel_costs.py
│   │   ├── seasonal_optimizer.py
│   │   ├── qualifying.py
│   │   ├── synthetic_ranks.py
│   │   ├── entry_fees.py
│   │   ├── birth_dates.py
│   │   └── run_validation.py
│   ├── app/                      # Web interface (Streamlit)
│   │   ├── app.py
│   │   └── requirements.txt
│   └── scraping/                 # Data collection scripts
├── tests/
└── outputs/
```

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | ✅ Complete | Project setup, charter, roadmap, repo structure |
| Phase 1 | ✅ Complete | Data acquisition — ATP & WTA match, ranking, and profile data |
| Phase 2 | ✅ Complete | Win probability model, Monte Carlo simulation engine |
| Phase 3 | ✅ Complete | Tournament economics, travel costs, seasonal optimizer |
| Phase 4 | 🟡 In Progress | Web interface (Streamlit app) |
| Phase 5 | ⬚ Planned | Full-season portfolio optimization, multi-sport expansion |

## Tech Stack

- **Core Engine**: Python (modeling, simulation, optimization)
- **Data Pipeline**: Python + R (scraping, cleaning, feature engineering)
- **Web App**: Streamlit
- **Data Storage**: CSV / JSON (BigQuery planned for scale)

## Current Model vs Full Vision

| Dimension | Current (MVP) | Full Vision |
|-----------|--------------|-------------|
| Scope | Single tournament window | Full season calendar |
| Costs | Entry fees + estimated travel | Actual travel, accommodation, coaching |
| Returns | Prize money | Prize money + ranking points + sponsorship value |
| Constraint | Budget cap per window | Annual budget with cash flow timing |
| Output | Top-N schedules for a window | Complete seasonal portfolio with alternatives |
| Optimization | Grid search over combinations | Dynamic programming / genetic algorithm |

## Key Documents

- [Project Charter v2](docs/project-management/PROJECT_CHARTER_v2.docx)
- [Product Roadmap](docs/project-management/PRODUCT_ROADMAP.docx)
- [MVP Design Document](docs/MVP_Design_Document.docx)
- [Model Validation Report](docs/validation_report_v2.md)

## License

This project is for personal/educational use.

---

*Built by Eric Schaap with assistance from Claude*
