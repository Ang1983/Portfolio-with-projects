# Formula 1 Pit-Stop Strategy Analysis

## Project Overview

This project is an exploratory data analysis (EDA) of Formula 1 racing data, aimed at understanding how **pit-stop strategy** (timing and tire compound selection) influences the **final race position** of drivers. The study combines data from multiple sources and applies statistical hypothesis testing to validate key assumptions about race strategy effectiveness.

The analysis is conducted on data from the **2023–2024 F1 seasons**.

## Objectives & Hypotheses

The main goal is to identify statistically significant relationships between pit-stop strategy, track characteristics, weather conditions, and final race results.

### Hypotheses Tested:

| # | Hypothesis | Statistical Test |
|---|------------|------------------|
| H1 | On street circuits, pit stops are performed significantly earlier than on high-speed circuits | Mann-Whitney U |
| H2 | Tire degradation at pit-stop time differs by track type | Mann-Whitney U |
| H3 | Tire compound selection depends on weather conditions (rainfall) | Chi-square |
| H4 | Tire choice strategy significantly affects the driver's final position | Kruskal-Wallis |
| H5 | There is a positive correlation between air temperature and tire degradation | Spearman |

## Data Sources

The analysis integrates data from **5 distinct datasets**:

| Dataset | Source | Content |
|---------|--------|---------|
| `pitstops.csv` | [muharsyad/formula-one-datasets](https://github.com/muharsyad/formula-one-datasets) | Pit-stop timing and frequency |
| `races.csv` / `drivers.csv` | [muharsyad/formula-one-datasets](https://github.com/muharsyad/formula-one-datasets) | Race and driver metadata |
| `f1_strategy_dataset_v4.csv` | [Kaggle: vanshjasuja16](https://www.kaggle.com/datasets/vanshjasuja16/f1-strategy-dataset-pit-stop-prediction) | Tire compounds and lap-by-lap data |
| `weather_2023.csv` / `weather_2024.csv` | [Kaggle: mariyakostyrya](https://www.kaggle.com/datasets/mariyakostyrya/formula-1-weather-info-1950-2024) | Meteorological conditions per race |
| `circuits.csv` | [Kaggle: meruvakodandasuraj](https://www.kaggle.com/datasets/meruvakodandasuraj/formula-1-race-intelligence-20102026) | Track type classification |

## Methodology

### Data Pipeline (ETL)
1. **Extract** — Load data from multiple CSV sources and GitHub repositories
2. **Transform** — Merge datasets on common keys (`raceId`, `season`, `driverId`), handle missing values, unify naming conventions
3. **Load** — Produce a single consolidated analytical dataset

### Statistical Analysis
- **Non-parametric tests** were chosen due to the non-normal distribution of race data (verified via histograms and boxplots)
- **Feature engineering**: track type classification, rainfall indicator, compound encoding
- **Correlation analysis**: Spearman rank correlation for ordinal and non-normally distributed variables

### Tools & Libraries
- **Python 3.9+**
- `pandas`, `numpy` — data manipulation
- `matplotlib`, `seaborn` — visualization
- `scipy.stats` — statistical testing

## Key Findings

### 1. Track Type vs. Pit-Stop Lap
> **H1 was NOT confirmed** (p = 0.7726)
> 
> No statistically significant difference in pit-stop timing between street and permanent circuits.

### 2. Tire Degradation by Track Type
> **H2 was confirmed** (p < 0.0001)
> 
> Tire degradation levels differ significantly depending on track characteristics.

### 3. Weather Impact on Tire Choice
> **H3 was confirmed** (p < 0.0001)
> 
> Rainfall significantly influences the choice of tire compound (INTERMEDIATE and WET compounds appear predominantly in wet conditions).

### 4. Tire Strategy vs. Final Position
> **H4 was partially confirmed**:
> - In **dry conditions**: tire choice has a significant impact (p = 0.0412). HARD tires yield the best median position (9.0), followed by MEDIUM (11.0) and SOFT (13.0).
> - In **wet conditions**: no significant impact (p = 0.3251) — driver skill and safety factors dominate.

### 5. Temperature vs. Degradation
> **H5 was confirmed** (Spearman ρ = 0.306, p < 0.0001)
> 
> A statistically significant positive correlation exists between air temperature and tire degradation.

### 6. Strongest Predictor
> **Starting Grid position** shows the strongest correlation with final position (ρ = 0.77), confirming that qualifying performance is the dominant factor in race outcome.

## Project Structure
```markdown
f1-pitstop-analysis/
├── Formula_1_training_set.ipynb   # Main analysis notebook
└── README.md                       # Project documentation
```

### Future Work
- Build a predictive ML model (Random Forest / XGBoost) to forecast finishing position based on strategy features
- Analyze undercut/overcut strategies and their success rates
- Incorporate driver-specific performance metrics

### Acknowledgments
- Datasets sourced from Kaggle and GitHub
- Inspired by the strategic complexity of Formula 1 racing

