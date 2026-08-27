# HilmarCorp — Digital Gold V4.1.1 Gel

Statut : **PASS**

## Spécification certifiée

- Cœur factoriel : actions, dollar, taux réel 10 ans.
- VIX : extension orthogonalisée + analyses conditionnelles, hors cœur primaire.
- Crédit : BAA10Y séparé ; HY OAS récent isolé.
- Inflation : CPI NSA associé aux dates effectives de publication BLS.
- Conditionnement inflation quotidien : information disponible à la clôture précédente.
- Bitcoin : prix observé exactement à la clôture effective NYSE Arca, y compris clôtures anticipées.
- NFCI : classification ex post uniquement ; aucune lecture point-in-time.
- Queues : résultats synthétisés par épisodes dont les fenêtres sélectionnées ne se chevauchent pas.

## Couverture

- Observations de rendement actifs : 2262.
- Observations cœur factoriel : 2262.
- Couverture du cœur : 100.00 %.
- Début cœur : +0 jour(s) ouvré(s).
- Fin cœur : 0 jour(s) ouvré(s) avant la dernière observation actifs.

## Régression primaire — horizon 1 jour

| Facteur | β BTC | β or | Δβ BTC-or | p(Δβ=0) |
|---|---:|---:|---:|---:|
| Actions américaines | 0.856020 | 0.010853 | 0.845167 | 0.000000 |
| Dollar large | -0.886950 | -1.027109 | 0.140159 | 0.648155 |
| Taux réel US 10 ans | -0.016357 | -0.057386 | 0.041028 | 0.022854 |

## Test conjoint d'égalité des sensibilités

- Wald conjoint : χ²(3) = 78.3645, p = 6.8832533e-17.

## Alignement BTC / NYSE Arca

- Clôtures anticipées détectées : 19.
- Clôtures anticipées avec prix BTC exact : 19.
- Séances BTC exactes manquantes : 2 (2017-09-06, 2018-02-08).

## Queues par épisodes indépendants

- baa_credit_widening_top_10pct : 17 épisode(s), fenêtres non chevauchantes = True.
- baa_credit_widening_top_5pct : 11 épisode(s), fenêtres non chevauchantes = True.
- dollar_fall_bottom_10pct : 27 épisode(s), fenêtres non chevauchantes = True.
- equity_bottom_10pct : 18 épisode(s), fenêtres non chevauchantes = True.
- equity_bottom_5pct : 11 épisode(s), fenêtres non chevauchantes = True.
- hy_oas_recent_widening_top_10pct : 8 épisode(s), fenêtres non chevauchantes = True.
- nfci_ex_post_stress_top_10pct : 5 épisode(s), fenêtres non chevauchantes = True.
- real_rate_rise_top_10pct : 15 épisode(s), fenêtres non chevauchantes = True.
- vix_change_top_10pct : 26 épisode(s), fenêtres non chevauchantes = True.
- vix_change_top_5pct : 19 épisode(s), fenêtres non chevauchantes = True.
- vix_level_ge_30 : 13 épisode(s), fenêtres non chevauchantes = True.

## Crédit isolé

- credit_baa_standalone: n = 2262 sur la fenêtre disponible.
- hy_oas_recent_standalone: n = 750 sur la fenêtre disponible.

## Inflation

- Publications CPI exploitables : 107.
- Aucune surprise d'inflation n'est inférée sans consensus de marché.
- L'accélération mesure la variation du taux d'inflation publié entre deux publications successives.

## Tests de certification

```json
{
  "index_unique": true,
  "index_monotonic": true,
  "btc_positive": true,
  "gold_positive": true,
  "arcx_calendar_session_coverage": 1.0,
  "arcx_calendar_all_gld_dates_pass": true,
  "arcx_early_close_sessions": 19,
  "arcx_early_close_exact_btc_matches": 19,
  "arcx_early_close_alignment_pass": true,
  "btc_missing_sessions_count": 2,
  "btc_missing_sessions": [
    "2017-09-06",
    "2018-02-08"
  ],
  "btc_missing_share": 0.000882223202470225,
  "btc_missing_sessions_pass": true,
  "asset_return_obs": 2262,
  "core_return_obs": 2262,
  "core_sample_coverage_ratio": 1.0,
  "core_sample_coverage_pass": true,
  "core_start_lag_business_days": 0,
  "core_end_lag_business_days": 0,
  "core_start_pass": true,
  "core_end_pass": true,
  "core_factor_coverage": {
    "equity": 0.9995584988962473,
    "usd": 0.9995584988962473,
    "real_rate": 0.9995584988962473
  },
  "core_factor_coverage_pass": true,
  "forbidden_factor_in_core": false,
  "core_factor_set_exact": true,
  "primary_regression_n": 2262,
  "primary_regression_n_pass": true,
  "cpi_release_count": 115,
  "cpi_release_unique_reference_months": true,
  "cpi_all_releases_causal": true,
  "cpi_minimum_release_count_pass": true,
  "loo_all_years_remove_rows": true,
  "loo_min_rows_removed": 91,
  "loo_min_removal_ratio_vs_calendar": 0.978494623655914,
  "hy_recent_isolated": true,
  "primary_joint_wald_present": true,
  "primary_joint_wald_chi2": 78.36454955707579,
  "primary_joint_wald_df": 3,
  "primary_joint_wald_p": 6.88325332861443e-17,
  "primary_joint_wald_finite": true,
  "nfci_explicitly_ex_post": true,
  "nfci_absent_from_core": true,
  "tail_episode_outputs_present": true,
  "tail_selected_windows_non_overlapping": true,
  "tail_episode_min_count": 5,
  "pass": true
}
```

## Règle de publication

Un PASS certifie la cohérence de la construction et la couverture annoncée. Il ne certifie ni une relation causale, ni une performance future.