# -*- coding: utf-8 -*-
"""
baseline_rules.py — Baseline simple (sin ML) para fraude:
- Score heurístico basado en Amount y |V1| (señales fuertes en el dataset)
- Umbral por cuantil de negativos para controlar FPs
- Reporta PR-AUC, F1 y precision/recall@k

Uso (ejemplo):
  python .\src\baseline_rules.py --input .\data\processed\test.csv --outdir .\reports --k 100 500
"""

from __future__ import annotations
import argparse, json, os
from datetime import datetime
import numpy as np
import pandas as pd

from metrics import pr_auc, f1_fraud, multi_k

def make_score(df: pd.DataFrame) -> np.ndarray:
    """
    Heurística robusta y rápida:
    - Normaliza Amount en [0,1] por cuantiles de no-fraude
    - Combina con |V1| normalizado (si existe V1)
    score = 0.7 * amount_norm + 0.3 * v1_norm
    """
    df = df.copy()
    if "Amount" not in df.columns:
        raise ValueError("Falta columna 'Amount'")

    # Separar no-fraude para estimar cuantiles robustos
    nonfraud = df[df.get("Class", 0) == 0]["Amount"].astype("float64")
    if len(nonfraud) == 0:
        nonfraud = df["Amount"].astype("float64")

    q01 = float(np.quantile(nonfraud, 0.01))
    q99 = float(np.quantile(nonfraud, 0.99))
    denom = max(q99 - q01, 1e-6)

    amount_norm = (df["Amount"].astype("float64") - q01) / denom
    amount_norm = amount_norm.clip(lower=0.0, upper=3.0) / 3.0  # recorte suave

    if "V1" in df.columns:
        v1_abs = df["V1"].astype("float64").abs()
        v1_q99 = float(np.quantile(v1_abs, 0.99))
        v1_norm = (v1_abs / max(v1_q99, 1e-6)).clip(0.0, 3.0) / 3.0
    else:
        v1_norm = np.zeros(len(df), dtype="float64")

    score = 0.7 * amount_norm + 0.3 * v1_norm
    return score.astype("float64").values

def pick_threshold(scores: np.ndarray, y_true: np.ndarray | None) -> float:
    """
    Umbral = percentil 99.5% de los scores en clase 0 (si está disponible),
    para limitar FPs. Si no hay etiquetas, usar percentil 99% global.
    """
    if y_true is not None and len(y_true) == len(scores) and y_true.sum() != len(y_true):
        neg_scores = scores[(y_true == 0)]
        if len(neg_scores) > 0:
            return float(np.quantile(neg_scores, 0.995))
    return float(np.quantile(scores, 0.99))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV de entrada (usar test.csv del Paso 3 para baseline)")
    ap.add_argument("--outdir", default=os.path.join("reports"), help="Directorio de salida de reportes")
    ap.add_argument("--k", nargs="+", type=int, default=[100, 500], help="Valores de k para precision/recall@k")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.input)

    if "Class" not in df.columns:
        raise ValueError("El CSV debe contener columna 'Class' (0/1)")

    y_true = df["Class"].astype(int).values
    scores = make_score(df)

    # Umbral por cuantil de negativos
    thr = pick_threshold(scores, y_true)
    y_pred = (scores >= thr).astype(int)

    # Métricas
    out = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": os.path.abspath(args.input),
        "n_samples": int(len(df)),
        "positives": int(y_true.sum()),
        "threshold": thr,
        "metrics": {
            "pr_auc": pr_auc(y_true, scores),
            "f1_fraud": f1_fraud(y_true, y_pred),
            "by_k": multi_k(y_true, scores, args.k),
        },
    }

    fname = f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    fpath = os.path.join(args.outdir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK → baseline guardado en: {fpath}")
    print(f"PR-AUC={out['metrics']['pr_auc']:.4f}  F1={out['metrics']['f1_fraud']:.4f}")
    for k, d in out["metrics"]["by_k"].items():
        print(f"k={k:>5}  precision@k={d['precision_at_k']:.4f}  recall@k={d['recall_at_k']:.4f}")

if __name__ == "__main__":
    main()
