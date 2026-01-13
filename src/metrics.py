# -*- coding: utf-8 -*-
"""
metrics.py — Métricas para fraude:
- PR-AUC (average precision)
- F1 (clase fraude = 1)
- precision@k, recall@k para k en una lista
- percentiles de latencia (si se proveen)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics import average_precision_score, f1_score

def pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    y_true = np.asarray(y_true).astype(int)
    y_score = np.asarray(y_score).astype(float)
    if y_true.sum() == 0:
        return 0.0
    return float(average_precision_score(y_true, y_score))

def f1_fraud(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    if y_true.sum() == 0 and y_pred.sum() == 0:
        return 0.0
    return float(f1_score(y_true, y_pred, pos_label=1))

def topk_mask(y_score: np.ndarray, k: int) -> np.ndarray:
    n = len(y_score)
    k = int(min(max(k, 0), n))
    if k == 0:
        return np.zeros(n, dtype=bool)
    idx = np.argpartition(-y_score, k-1)[:k]
    mask = np.zeros(n, dtype=bool)
    mask[idx] = True
    return mask

def precision_recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> Tuple[float, float]:
    y_true = np.asarray(y_true).astype(int)
    m = topk_mask(y_score, k)
    tp = int((y_true[m] == 1).sum())
    denom = m.sum()
    prec = (tp / denom) if denom > 0 else 0.0
    rec = (tp / max(int((y_true == 1).sum()), 1))
    return float(prec), float(rec)

def multi_k(y_true: np.ndarray, y_score: np.ndarray, ks: List[int]) -> Dict[str, Dict[str, float]]:
    out = {}
    for k in ks:
        p, r = precision_recall_at_k(y_true, y_score, int(k))
        out[str(k)] = {"precision_at_k": p, "recall_at_k": r}
    return out

def latency_percentiles(latencies_ms: Optional[np.ndarray]) -> Dict[str, float]:
    if latencies_ms is None or len(latencies_ms) == 0:
        return {}
    q = np.percentile(latencies_ms, [50, 95, 99]).astype(float)
    return {"p50_ms": q[0], "p95_ms": q[1], "p99_ms": q[2]}
