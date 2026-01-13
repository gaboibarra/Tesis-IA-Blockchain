# -*- coding: utf-8 -*-
"""
Compara último baseline_*.json vs último rf_*.json
Genera reports/eval_*.md con deltas y banderas de aceptación.
"""
import os, glob, json, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS = os.path.join(ROOT, "reports")

def load_last(pattern):
    paths = sorted(glob.glob(os.path.join(REPORTS, pattern)))
    if not paths:
        raise SystemExit(f"No se encontró {pattern} en {REPORTS}")
    with open(paths[-1], "r", encoding="utf-8") as f:
        return json.load(f), paths[-1]

def main():
    base, base_p = load_last("baseline_*.json")
    rf, rf_p = load_last("rf_*.json")

    b = base["metrics"]
    r = rf["metrics"]["test"]

    # Deltas
    d_pr = r["pr_auc"] - b["pr_auc"]
    d_f1 = r["f1_fraud"] - b["f1_fraud"]

    def get_k(d, k):
        return d["by_k"].get(str(k), {"precision_at_k":0,"recall_at_k":0})
    k_vals = [100, 500]
    deltas_k = {}
    for k in k_vals:
        bk = get_k(b, k); rk = get_k(r, k)
        deltas_k[k] = {
            "Δprecision@k": rk["precision_at_k"] - bk["precision_at_k"],
            "Δrecall@k": rk["recall_at_k"] - bk["recall_at_k"]
        }

    # Criterios (del enunciado)
    accepts = []
    if d_pr >= 0.05: accepts.append("ΔPR-AUC ≥ 0.05")
    for k in k_vals:
        if deltas_k[k]["Δrecall@k"] >= 0.10:
            accepts.append(f"Δrecall@{k} ≥ 10 pp (misma precision@k)")
    # ΔFP ≤ −15% requeriría matriz de confusión; omitimos o marcamos como N/A

    md = []
    md.append(f"# Evaluación RF vs Baseline ({datetime.datetime.now():%Y-%m-%d %H:%M})")
    md.append("")
    md.append(f"- Baseline: `{os.path.basename(base_p)}`")
    md.append(f"- RF: `{os.path.basename(rf_p)}`")
    md.append("")
    md.append(f"**ΔPR-AUC:** {d_pr:+.4f}  |  **ΔF1:** {d_f1:+.4f}")
    for k in k_vals:
        dpk = deltas_k[k]["Δprecision@k"]
        drk = deltas_k[k]["Δrecall@k"]
        md.append(f"- k={k}: Δprecision@k={dpk:+.4f}  Δrecall@k={drk:+.4f}")
    md.append("")
    md.append("**Criterios cumplidos:** " + (", ".join(accepts) if accepts else "N/A"))
    md_txt = "\n".join(md)

    outp = os.path.join(REPORTS, f"eval_{datetime.datetime.now():%Y%m%d_%H%M%S}.md")
    with open(outp, "w", encoding="utf-8") as f:
        f.write(md_txt)
    print(outp)
    print(md_txt)

if __name__ == "__main__":
    main()
