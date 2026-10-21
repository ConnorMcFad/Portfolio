# Spotify Tracks: What Audio Features Can (and Can't) Tell Us About Popularity

An end-to-end analysis of ~114,000 Spotify tracks: SQL exploration, K-Means clustering into track archetypes, a random forest popularity model, and SHAP explainability.

> **Key question:** How much of a track's popularity can be explained by its audio characteristics alone?

## Key Findings

- **Audio features alone explain about 25% of the variance in popularity** (R² = 0.2465, MAE = 13.6 points on a 0-100 scale). That is a meaningful signal, but most of what drives popularity, such as artist reach, marketing, playlist placement, and timing, is not in the audio.
- **Acousticness, duration, and valence are the strongest drivers of predicted popularity (SHAP).** Highly acoustic and high-valence tracks tend to score lower, while louder and more danceable tracks score higher. Tempo contributes little.
- **Tracks fall into 5 audio archetypes (K-Means).** The tracks fell into 5 audio archetypes using k-means clusters. I then labeled these as: 'Chill Pop', 'Dark & Melancholic', 'Happy & Euphoric', 'Live Performance',and 'Intense & Dark'.
- **SQL Findings:** K-Pop, pop-film, and Metal had the highest average popularity scores for this time window. When filtering on artists with 10 or more tracks, familar artists like Bad Bunny, Travis Scott, and Frank Ocean have the highest average popularity. Comedy and sad music tracks had the highest percentage of explicit tracks.

## Dataset

- **Source:** Spotify Tracks Dataset (~114k tracks)
- **Contents:** Track metadata plus audio features (acousticness, duration, valence, loudness, energy, danceability, speechiness, tempo) and a popularity score (0-100)
- **Cleaning:** The dataset was fairly curated and other than scaling the technical features used (not necessary for tree models, but would effect clustering), I only had to remove duplicate entries.

## Methodology

1. **SQL exploration (SQLite).** Loaded the data into an in-memory SQLite database and used CTEs and window functions to profile genres, artists, and popularity distributions.
2. **Feature engineering and scaling.** Applied feature-specific scaling (MinMaxScaler vs. StandardScaler) based on each variable's distribution rather than blanket normalization.
3. **Clustering (K-Means).** Grouped tracks into archetypes by audio profile. I chose **k = 5** by plotting inertia (elbow method) and silhouette scores across candidate values of k and picking the value that balanced compactness, cluster separation, and interpretability. I then ran a one-way ANOVA (scipy.stats.f_oneway) to test whether mean popularity differs across the 5 archetypes: F = 98.96, p = 3.4e-84, effect size η² = 0.0044. The difference is statistically significant, but archetype membership explains only about 0.4% of the variance in popularity.
4. **Regression (random forest).** Predicted popularity from the 8 audio features using an 80/20 train/test split, evaluated on the held-out test set.
5. **Explainability (SHAP).** Used TreeExplainer on a random sample of 2,000 test tracks (for speed) to show which features push predictions up or down.

### Cluster labels are for interpretation only

Archetype labels are derived from the same audio features the regression uses, so they were **not** model inputs. The model sees only the audio features, and the archetypes were used afterward to compare popularity and SHAP patterns across track types.

## Results

| Model | MAE | RMSE | R² |
|-------|-----|------|-----|
| Random forest | 13.62 | 17.77 | 0.2465 |

R² = 0.2465 means the model explains about 25% of the variance in popularity beyond simply predicting the average track. An average error of about 14 points shows that audio features alone cannot pin down how popular a track will be.


**Reading the SHAP plot:** features are ranked by overall impact, red dots are high feature values, and dots to the right push predicted popularity up. These are patterns the model learned from this dataset, not causal effects, and correlated features such as energy, loudness, and acousticness share credit.

## Tech Stack

Python (pandas, NumPy, scikit-learn, SHAP, seaborn, matplotlib) · SQL (SQLite) · Jupyter Notebook


## Limitations and Next Steps

- Audio features alone cap predictive power; adding artist-level, playlist, or release-timing data would likely improve it.
- Next steps would be to compare against gradient boosting and a tuned random forest, and test whether adding genre metadata lifts R² beyond what audio features alone can explain. Additional data would likely improve performance and verify that the main limit is lack of predictive information in the audio features.

## Author

**Connor McFadden** - [LinkedIn](https://www.linkedin.com/in/connor-mcfadden-ab5a41395/)