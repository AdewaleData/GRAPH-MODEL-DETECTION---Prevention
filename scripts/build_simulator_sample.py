"""Rebuild artifacts/data/cicddos_sample.csv with benign + DDoS rows for live demo."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "CICDDoS.csv"
OUT = ROOT / "artifacts" / "data" / "cicddos_sample.csv"
BENIGN_TARGET = 1200
ATTACK_TARGET = 3800


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing dataset: {SRC}")

    chunks: list[pd.DataFrame] = []
    benign_n = attack_n = 0

    for chunk in pd.read_csv(SRC, chunksize=20000):
        chunk.columns = [c.strip() for c in chunk.columns]
        if benign_n < BENIGN_TARGET:
            take = chunk[chunk["Label"] == "BENIGN"].head(BENIGN_TARGET - benign_n)
            if len(take):
                chunks.append(take)
                benign_n += len(take)
        if attack_n < ATTACK_TARGET:
            take = chunk[chunk["Label"] != "BENIGN"].head(ATTACK_TARGET - attack_n)
            if len(take):
                chunks.append(take)
                attack_n += len(take)
        if benign_n >= BENIGN_TARGET and attack_n >= ATTACK_TARGET:
            break

    mixed = pd.concat(chunks, ignore_index=True).sample(frac=1, random_state=42)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mixed.to_csv(OUT, index=False)
    print(f"Wrote {len(mixed)} rows -> {OUT}")
    print(mixed["Label"].value_counts())


if __name__ == "__main__":
    main()
