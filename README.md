# Tennis Tournament Optimizer

> A data-driven tool to help lower-level tennis players make smarter tournament decisions — maximizing competitive growth while maintaining financial sustainability.

## 🎯 Vision

Help players answer: *"Given my current level and budget, which tournaments should I play this year to maximize my development while staying financially sustainable?"*

## 📊 Approach

- **Data**: Historical match and tournament data from Coretennis.net (and potentially other sources)
- **Model**: Monte Carlo simulation to estimate round-reach probabilities
- **Output**: Expected ROI per tournament combining win probability with financial factors

## 📁 Repository Structure

```
tennis-tournament-optimizer/
├── docs/
│   ├── project-management/    # Charter, roadmap, status reports
│   └── technical/             # Architecture, data dictionaries
├── data/
│   ├── raw/                   # Unprocessed scraped data
│   └── processed/             # Cleaned, analysis-ready data
├── src/
│   ├── scraping/              # Python scraping scripts
│   ├── modeling/              # R simulation & modeling code
│   └── app/                   # Shiny web application
├── tests/                     # Test scripts
└── outputs/                   # Generated reports, figures
```

## 🚀 Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | 🟢 In Progress | Project Setup & Planning |
| Phase 1 | ⚪ Not Started | Data Acquisition & Exploration |
| Phase 2 | ⚪ Not Started | Core Simulation Model |
| Phase 3 | ⚪ Not Started | Financial Layer |
| Phase 4 | ⚪ Not Started | MVP Web Interface |
| Phase 5 | ⚪ Not Started | Iteration & Enhancement |

## 🛠️ Tech Stack

- **Scraping**: Python (BeautifulSoup/Scrapy)
- **Modeling**: R
- **Database**: BigQuery / SQLite (dev)
- **Web App**: R Shiny
- **Project Management**: GitHub Issues & Projects

## 📄 Key Documents

- [Project Charter](docs/project-management/PROJECT_CHARTER.md)
- [Product Roadmap](docs/project-management/PRODUCT_ROADMAP.md) *(coming soon)*
- [Technical Architecture](docs/technical/ARCHITECTURE.md) *(coming soon)*

## 📝 License

This project is for personal/educational use.

---

*Built with assistance from Claude*
