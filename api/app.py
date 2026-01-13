# -*- coding: utf-8 -*-
"""
api/app.py — Flask API (puerto 5000)
- POST /score  { "features": {col: value, ...}, "tx_ref": "opcional" }
- Si la decisión es "segura" (score<thr) dispara evento on-chain (sin PII)
- /health para diagnóstico (RPC y contrato)
"""

import json, os, time, glob, hashlib
from typing import Dict, Any
from flask import Flask, request, jsonify
from joblib import load
import numpy as np
import pandas as pd

from .logging_mw import request_logger
from .chain import register_secure_tx, CONTRACT_ADDRESS, w3

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(ROOT, "models")
REPORTS_DIR = os.path.join(ROOT, "reports")

app = Flask(__name__)
request_logger(app)

_model = None
_features = None
_threshold = None

def _load_model_and_meta():
    global _model, _features, _threshold
    if _model is None:
        _model = load(os.path.join(MODELS_DIR, "model.joblib"))
    if _features is None:
        with open(os.path.join(MODELS_DIR, "features.json"), "r", encoding="utf-8") as f:
            _features = json.load(f)["features"]
    if _threshold is None:
        # Tomar el umbral del último rf_*.json
        paths = sorted(glob.glob(os.path.join(REPORTS_DIR, "rf_*.json")))
        if not paths:
            raise RuntimeError("No se encontró reports/rf_*.json con el umbral")
        with open(paths[-1], "r", encoding="utf-8") as f:
            rep = json.load(f)
        _threshold = float(rep["threshold"]["value"])

def _vectorize(feats: Dict[str, Any]) -> np.ndarray:
    # Asegurar orden y tipos
    row = [float(feats.get(col, 0.0)) for col in _features]
    return np.array(row, dtype=np.float32).reshape(1, -1)

@app.get("/health")
def health():
    try:
        _load_model_and_meta()
        rpc_ok = bool(w3.is_connected())
        return jsonify({
            "status": "ok",
            "rpc_connected": rpc_ok,
            "contract_address": CONTRACT_ADDRESS,
            "features": len(_features),
            "threshold": _threshold
        })
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.post("/score")
def score():
    """
    Request:
    { "features": {col:value,...}, "tx_ref": "opcional" }
    Respuesta:
    {
      "score": float, "label": 0|1, "secure": bool,
      "decision_id": "0x..", "tx_ref_hash": "0x..",
      "onchain": {"tx_hash":"0x..","blockNumber":N} | {"skipped":True} | null
    }
    """
    t0 = time.perf_counter()
    _load_model_and_meta()

    data = request.get_json(force=True) or {}
    feats = data.get("features") or {}
    tx_ref = data.get("tx_ref") or ""

    vec = _vectorize(feats)
    # Probabilidad de clase 1 (fraude)
    if hasattr(_model, "predict_proba"):
        score = float(_model.predict_proba(vec)[:,1][0])
    else:
        # Normalizo decision_function a [0,1] si hiciera falta
        s = float(_model.decision_function(vec)[0])
        score = (s - (-10.0)) / (10.0 - (-10.0))

    label = int(score >= _threshold)  # 1 = fraude
    secure = bool(label == 0)

    # decision_id y txRefHash (sin PII): 32 bytes a partir de hash SHA256
    # decision_id: hash del vector + threshold + model path
    digest_dec = hashlib.sha256((str(vec.tolist()) + str(_threshold)).encode("utf-8")).hexdigest()
    decision_id = "0x" + digest_dec[:64]
    # txRefHash: hash de tx_ref (si no hay, hash del timestamp)
    base_txref = tx_ref or f"ts:{time.time_ns()}"
    digest_tx = hashlib.sha256(base_txref.encode("utf-8")).hexdigest()
    tx_ref_hash = "0x" + digest_tx[:64]

    onchain = None
    if secure:
        # Llamar al contrato (idempotente a nivel app)
        onchain = register_secure_tx(decision_id, tx_ref_hash)

    dt_ms = (time.perf_counter() - t0)*1000.0
    return jsonify({
        "score": score,
        "label": label,
        "secure": secure,
        "decision_id": decision_id,
        "tx_ref_hash": tx_ref_hash,
        "latency_ms": dt_ms,
        "onchain": onchain
    })

if __name__ == "__main__":
    # Puerto 5000; si hay colisión, usa 5050 y abrí el firewall (privada)
    app.run(host="127.0.0.1", port=5000, debug=False)


