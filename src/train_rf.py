# -*- coding: utf-8 -*-
"""
train_rf.py — RandomForest con umbral optimizado en val (modo f1 o cost)
Uso:
  python .\\src\\train_rf.py --data-dir .\\data\\processed --k 100 500 --th-mode f1 --n-estimators 200 --max-depth 16
"""

from __future__ import annotations
import os, sys, json, math, argparse
from datetime import datetime
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_curve, average_precision_score
from metrics import multi_k, pr_auc, f1_fraud

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _read_any(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".parquet":
        try:
            import pyarrow  # noqa
            return pd.read_parquet(path)
        except Exception:
            return pd.read_csv(path)
    return pd.read_csv(path)

def _features_and_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    cols = [c for c in df.columns if c != "Class"]
    X = df[cols].astype("float32")
    y = df["Class"].astype("int8").values
    return X, y

def _predict_scores(clf, X: pd.DataFrame) -> np.ndarray:
    if hasattr(clf, "predict_proba"):
        return clf.predict_proba(X)[:, 1].astype("float64")
    if hasattr(clf, "decision_function"):
        s = clf.decision_function(X).astype("float64")
        s = (s - s.min()) / (s.max() - s.min() + 1e-12)
        return s
    return clf.predict(X).astype("float64")

def _best_threshold_f1(y_true: np.ndarray, scores: np.ndarray):
    prec, rec, thr = precision_recall_curve(y_true, scores)
    f1s = (2 * prec * rec) / np.maximum(prec + rec, 1e-12)
    idx = int(np.nanargmax(f1s))
    best_thr = thr[idx-1] if (idx > 0 and (idx-1) < len(thr)) else 0.5
    return float(best_thr), float(np.nanmax(f1s))

def _best_threshold_cost(y_true: np.ndarray, scores: np.ndarray, fn_cost=5.0, fp_cost=1.0):
    prec, rec, thr = precision_recall_curve(y_true, scores)
    P = max(float(y_true.sum()), 1.0)
    best = (math.inf, 0.5)
    for i in range(len(thr)):
        p, r = prec[i], rec[i]
        if p <= 0: 
            continue
        tp = r * P
        fp = (1.0 - p) / p * tp
        fn = P - tp
        cost = fn_cost * fn + fp_cost * fp
        if cost < best[0]:
            best = (cost, thr[i])
    return float(best[1]), float(best[0])

def _report_block(y_true: np.ndarray, scores: np.ndarray, y_pred: np.ndarray, ks: List[int]) -> Dict:
    return {
        "pr_auc": pr_auc(y_true, scores),
        "f1_fraud": f1_fraud(y_true, y_pred),
        "by_k": multi_k(y_true, scores, ks)
    }

def _plot_pr_curve(y_true: np.ndarray, scores: np.ndarray, out_path: str):
    prec, rec, _ = precision_recall_curve(y_true, scores)
    ap = average_precision_score(y_true, scores)
    plt.figure()
    plt.step(rec, prec, where="post")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(f"PR Curve (AP={ap:.4f})")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join("data","processed"))
    ap.add_argument("--k", nargs="+", type=int, default=[100, 500])
    ap.add_argument("--th-mode", choices=["f1","cost"], default="f1")
    ap.add_argument("--fn-cost", type=float, default=5.0)
    ap.add_argument("--fp-cost", type=float, default=1.0)
    ap.add_argument("--n-estimators", type=int, default=200)
    ap.add_argument("--max-depth", type=int, default=16)
    ap.add_argument("--random-state", type=int, default=42)
    args = ap.parse_args()

    # Paths (parquet preferido, csv fallback)
    p_train = os.path.join(args.data_dir, "train.parquet")
    p_val   = os.path.join(args.data_dir, "val.parquet")
    p_test  = os.path.join(args.data_dir, "test.parquet")
    if not os.path.exists(p_train): p_train = os.path.join(args.data_dir, "train.csv")
    if not os.path.exists(p_val):   p_val   = os.path.join(args.data_dir, "val.csv")
    if not os.path.exists(p_test):  p_test  = os.path.join(args.data_dir, "test.csv")

    print(f"[RF] Leyendo: {p_train}, {p_val}, {p_test}")
    train = _read_any(p_train); val = _read_any(p_val); test = _read_any(p_test)
    X_tr, y_tr = _features_and_target(train)
    X_va, y_va = _features_and_target(val)
    X_te, y_te = _features_and_target(test)

    clf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        n_jobs=-1,
        class_weight="balanced",
        random_state=args.random_state,
    )
    clf.fit(X_tr, y_tr)

    s_va = _predict_scores(clf, X_va)
    s_te = _predict_scores(clf, X_te)

    if args.th_mode == "f1":
        thr, f1_best = _best_threshold_f1(y_va, s_va)
        th_info = {"mode": "f1", "best_f1_val": f1_best}
    else:
        thr, min_cost = _best_threshold_cost(y_va, s_va, fn_cost=args.fn_cost, fp_cost=args.fp_cost)
        th_info = {"mode": "cost", "fn_cost": args.fn_cost, "fp_cost": args.fp_cost, "min_cost_val": min_cost}

    y_va_pred = (s_va >= thr).astype(int)
    y_te_pred = (s_te >= thr).astype(int)

    rep_val = _report_block(y_va, s_va, y_va_pred, args.k)
    rep_te  = _report_block(y_te, s_te, y_te_pred, args.k)

    os.makedirs("models", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    dump(clf, os.path.join("models","model.joblib"))
    with open(os.path.join("models","features.json"), "w", encoding="utf-8") as f:
        json.dump({"features": list(X_tr.columns)}, f, ensure_ascii=False, indent=2)

    pr_path = os.path.join("reports","pr_curve.png")
    _plot_pr_curve(y_te, s_te, pr_path)

    out = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_dir": os.path.abspath(args.data_dir),
        "model": "RandomForestClassifier",
        "params": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "class_weight": "balanced",
            "random_state": args.random_state
        },
        "threshold": {"value": thr, **th_info},
        "metrics": {"val": rep_val, "test": rep_te},
        "artifacts": {
            "model_path": os.path.abspath(os.path.join("models","model.joblib")),
            "features_path": os.path.abspath(os.path.join("models","features.json")),
            "pr_curve": os.path.abspath(pr_path)
        }
    }
    outp = os.path.join("reports", f"rf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK → modelo guardado en models/model.joblib")
    print(f"Umbral seleccionado: {thr:.6f}  (modo={th_info['mode']})")
    print(f"Val:  PR-AUC={rep_val['pr_auc']:.4f}  F1={rep_val['f1_fraud']:.4f}")
    for k, d in rep_val["by_k"].items():
        print(f"Val k={k:>5}: precision@k={d['precision_at_k']:.4f}  recall@k={d['recall_at_k']:.4f}")
    print(f"Test: PR-AUC={rep_te['pr_auc']:.4f}  F1={rep_te['f1_fraud']:.4f}")
    for k, d in rep_te["by_k"].items():
        print(f"Test k={k:>5}: precision@k={d['precision_at_k']:.4f}  recall@k={d['recall_at_k']:.4f}")
    print(f"Reporte: {outp}")

if __name__ == "__main__":
    main()
