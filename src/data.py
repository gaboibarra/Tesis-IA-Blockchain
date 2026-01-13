# -*- coding: utf-8 -*-
"""
fraudchain - Paso 3: Data loader RAM-friendly + split out-of-time
Uso:
  python .\src\data.py --input .\data\creditcard.csv --outdir .\data\processed --sample-frac 0.30 --test-frac-time 0.20 --val-frac 0.10 --random-state 42
"""

import argparse, os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import StratifiedShuffleSplit

def _has_pyarrow():
    try:
        import pyarrow  # noqa
        return True
    except Exception:
        return False

def _bytes(n: int) -> str:
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def load_creditcard_csv(path: str) -> pd.DataFrame:
    cols = ["Time"] + [f"V{i}" for i in range(1,29)] + ["Amount","Class"]
    dtype = {c:"float32" for c in cols if c not in ("Time","Class")}
    dtype["Time"] = "float32"
    dtype["Class"] = "int8"
    df = pd.read_csv(path, usecols=lambda c: c in cols, dtype=dtype, low_memory=True)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {missing}")
    return df[cols]

def split_out_of_time(df: pd.DataFrame, test_frac_time: float, val_frac: float, random_state: int):
    if not (0.0 < test_frac_time < 0.9):
        raise ValueError("test_frac_time debe estar entre (0, 0.9)")
    if not (0.0 < val_frac < 0.5):
        raise ValueError("val_frac debe estar entre (0, 0.5)")

    t_min, t_max = float(df["Time"].min()), float(df["Time"].max())
    cutoff = t_min + (t_max - t_min) * (1.0 - test_frac_time)

    early = df[df["Time"] < cutoff].copy()
    late  = df[df["Time"] >= cutoff].copy()

    # si late quedó sin positivos, mover cutoff un poco
    if late["Class"].sum() == 0 and test_frac_time <= 0.85:
        cutoff = t_min + (t_max - t_min) * (1.0 - (test_frac_time + 0.05))
        early = df[df["Time"] < cutoff].copy()
        late  = df[df["Time"] >= cutoff].copy()

    # val estratificado en early (si hay ambas clases)
    if early["Class"].nunique() >= 2 and len(early) > 0:
        sss = StratifiedShuffleSplit(n_splits=1, test_size=val_frac, random_state=random_state)
        idx = np.arange(len(early))
        y   = early["Class"].values
        tr_idx, val_idx = next(sss.split(idx, y))
        train = early.iloc[tr_idx]
        val   = early.iloc[val_idx]
    else:
        # rarísimo: sin positivos o early vacío → split simple
        val = early.sample(frac=val_frac, random_state=random_state)
        train = early.drop(index=val.index)

    test = late
    return train, val, test

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default=os.path.join("data","processed"))
    ap.add_argument("--sample-frac", type=float, default=1.0)
    ap.add_argument("--test-frac-time", type=float, default=0.20)
    ap.add_argument("--val-frac", type=float, default=0.10)
    ap.add_argument("--random-state", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Leyendo: {args.input}")
    df = load_creditcard_csv(args.input)

    if 0 < args.sample_frac < 1.0:
        df = df.sample(frac=args.sample_frac, random_state=args.random_state)
        df = df.sort_values("Time", kind="stable").reset_index(drop=True)
        print(f"sample-frac={args.sample_frac:.2f} → {len(df):,} filas")

    print(f"Split OOT: test_frac_time={args.test_frac_time:.2f}  val_frac={args.val_frac:.2f}")
    train, val, test = split_out_of_time(df, args.test_frac_time, args.val_frac, args.random_state)

    mem = lambda x: _bytes(x.memory_usage(deep=True).sum())
    print(f"Memoria total={mem(df)}  train={mem(train)}  val={mem(val)}  test={mem(test)}")

    use_parquet = _has_pyarrow()
    def _save(dfp, name):
        p = os.path.join(args.outdir, f"{name}.{'parquet' if use_parquet else 'csv'}")
        if use_parquet:
            dfp.to_parquet(p, index=False)
        else:
            dfp.to_csv(p, index=False)
        return p

    p_train = _save(train, "train")
    p_val   = _save(val, "val")
    p_test  = _save(test, "test")

    summ = {
        "rows": { "total": int(len(df)), "train": int(len(train)), "val": int(len(val)), "test": int(len(test)) },
        "positives": { "total": int(df['Class'].sum()), "train": int(train['Class'].sum()), "val": int(val['Class'].sum()), "test": int(test['Class'].sum()) },
        "paths": { "train": p_train, "val": p_val, "test": p_test },
        "format": "parquet" if use_parquet else "csv",
        "params": { "sample_frac": args.sample_frac, "test_frac_time": args.test_frac_time, "val_frac": args.val_frac, "random_state": args.random_state }
    }
    sp = os.path.join(args.outdir, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(summ, f, ensure_ascii=False, indent=2)

    print(f"OK → guardado: {p_train}, {p_val}, {p_test}")
    print(f"Resumen: {sp}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(2)
