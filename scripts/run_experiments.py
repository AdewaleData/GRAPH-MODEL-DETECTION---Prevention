"""Run full multi-seed + victim hold-out experiments."""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")

from ddos_gnn.config import EXPERIMENT_SEEDS, MAX_FLOWS
from ddos_gnn.data_loader import load_cic_ddos, stratified_sample
from ddos_gnn.experiments import run_multi_seed_experiment, run_victim_holdout_experiment
from ddos_gnn.preprocessing import clean_dataframe, engineer_features, get_feature_columns

if __name__ == "__main__":
    df = stratified_sample(clean_dataframe(engineer_features(load_cic_ddos())), MAX_FLOWS)
    cols = get_feature_columns(df)
    report = run_multi_seed_experiment(max_flows=MAX_FLOWS, seeds=EXPERIMENT_SEEDS)
    holdout = run_victim_holdout_experiment(df, cols)
    print("Done.", report.get("paired_ttest_gcn_graph_vs_rf_flow_f1"), holdout)
