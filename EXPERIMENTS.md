# Experiment Protocol

## Primary task
Graph-window binary classification: attack vs benign traffic windows grouped by victim (destination) IP.

## Metrics reported
| Metric | Purpose |
|--------|---------|
| Accuracy | Overall correctness |
| Balanced accuracy | Class imbalance robustness |
| Precision / Recall / F1 | Security trade-offs |
| Specificity / FPR / FNR | False alarm vs miss rates |
| MCC | Correlation on imbalanced data |
| ROC-AUC / PR-AUC | Ranking quality |
| Brier score | Probability calibration |
| Bootstrap 95% CI | Uncertainty on F1 and AUC |

## Fair comparisons
1. **RF (per-flow)** — standard tabular baseline
2. **RF (graph-window)** — same windows as GNN, mean flow probability
3. **GCN / GAT (graph)** — proposed method with tuned threshold
4. **GCN (flow-mapped)** — graph predictions propagated to member flows

## Statistical tests
- **Bootstrap CI** on test set (1000 resamples)
- **McNemar test** vs graph-window RF on paired graph predictions
- **Multi-seed** mean ± std over `EXPERIMENT_SEEDS`
- **Paired t-test** on F1 across seeds (GCN graph vs RF flow)

## Generalization
- **Victim hold-out**: entire destination IPs excluded from training

## Reproduce
```bash
python scripts/run_pipeline_test.py
python scripts/run_experiments.py
jupyter nbconvert --execute notebooks/CICDDoS_GNN_DDoS_Detection.ipynb
```

Results: `artifacts/experiments/results.json`
