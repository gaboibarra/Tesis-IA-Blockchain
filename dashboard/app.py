# -*- coding: utf-8 -*-
import os, json, glob, shutil
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output
from web3 import Web3
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS = os.path.join(ROOT, "reports")
ENV = os.path.join(ROOT, ".env")
EVENTS_CSV = os.path.join(ROOT, "events.csv")

# ---------- helpers de carga ----------
def load_rf():
    paths = sorted(glob.glob(os.path.join(REPORTS, "rf_*.json")))
    if not paths: 
        return None
    with open(paths[-1], "r", encoding="utf-8") as f:
        return json.load(f)

def load_env():
    out = {}
    if os.path.exists(ENV):
        with open(ENV, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k,v = line.strip().split("=",1); out[k]=v
    return out

def load_events(n=200):
    if not os.path.exists(EVENTS_CSV):
        return pd.DataFrame(columns=["decision_id_hex","tx_ref_hash_hex","tx_hash","block_number"])
    return pd.read_csv(EVENTS_CSV).tail(n)

def load_e2e_summary():
    p = os.path.join(REPORTS, "e2e_summary.json")
    if not os.path.exists(p): 
        return None
    try:
        with open(p,"r",encoding="utf-8") as f: 
            return json.load(f)
    except Exception:
        return None

# ---------- componentes ----------
def pr_curve_component():
    img_path = os.path.join(REPORTS, "pr_curve.png")
    assets_dir = os.path.join(os.path.dirname(__file__), "assets"); os.makedirs(assets_dir, exist_ok=True)
    dst_img = os.path.join(assets_dir, "pr_curve.png")
    if os.path.exists(img_path):
        try: shutil.copyfile(img_path, dst_img)
        except Exception: pass
        return html.Img(src="/assets/pr_curve.png", style={"maxWidth":"100%","borderRadius":"8px","boxShadow":"0 2px 10px rgba(0,0,0,.05)"})
    fig = go.Figure(); fig.update_layout(height=380, margin=dict(l=10,r=10,t=30,b=10), title="PR Curve")
    return dcc.Graph(figure=fig, config={"displayModeBar": False})

def kpi_card(title, value):
    return html.Div(className="card shadow-sm mb-3", style={"borderRadius":"16px"}, children=[
        html.Div(className="card-body", children=[
            html.Div(title, className="text-secondary", style={"fontSize":"0.9rem"}),
            html.Div(str(value), style={"fontSize":"1.8rem","fontWeight":"700","lineHeight":"1.1"})
        ])
    ])

# ---------- estado inicial ----------
rf = load_rf() or {"metrics":{"test":{"pr_auc":0,"f1_fraud":0,"by_k":{}}}, "threshold":{"value":0}}
env = load_env()
RPC_URL = env.get("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = env.get("CONTRACT_ADDRESS","(no configurado)")
try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 5}))
    rpc_ok = w3.is_connected()
except Exception:
    rpc_ok = False

test = rf["metrics"]["test"]; byk = test.get("by_k", {})
k100 = byk.get("100", {"precision_at_k":0,"recall_at_k":0})
k500 = byk.get("500", {"precision_at_k":0,"recall_at_k":0})

external_stylesheets = ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"]
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "FraudChain Dashboard"

# ---------- layout ----------
app.layout = html.Div(className="container-fluid py-4", children=[
    html.Div(className="d-flex align-items-center mb-4", children=[
        html.H2("FraudChain — KPIs y On-chain (v2+)", className="me-3"),
        html.Span("RPC: healthy" if rpc_ok else "RPC: down",
                  className=f"badge rounded-pill ms-2 {'bg-success' if rpc_ok else 'bg-danger'}"),
        html.Span("Contract", className="badge bg-secondary ms-3"),
        html.Code(CONTRACT_ADDRESS, className="ms-2", style={"fontFamily":"ui-monospace,Consolas,Menlo,monospace"}),
        html.Span(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id="ts-badge", className="badge bg-info ms-3")
    ]),

    # KPIs de modelo + operacionales (3 placeholders)
    html.Div(className="row g-3", children=[
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("Test PR-AUC", f"{test.get('pr_auc',0):.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("Test F1 (fraude)", f"{test.get('f1_fraud',0):.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("precision@100", f"{k100['precision_at_k']:.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("recall@100", f"{k100['recall_at_k']:.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("precision@500", f"{k500['precision_at_k']:.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("recall@500", f"{k500['recall_at_k']:.3f}")),
        html.Div(className="col-12 col-sm-6 col-lg-4", children=kpi_card("Threshold", f"{rf['threshold']['value']:.4f}")),
        # Operacionales (se rellenan por callback)
        html.Div(id="card-p95s", className="col-12 col-sm-6 col-lg-4"),
        html.Div(id="card-p95e", className="col-12 col-sm-6 col-lg-4"),
        html.Div(id="card-corr", className="col-12 col-sm-6 col-lg-4"),
    ]),

    html.Hr(className="my-4"),

    html.Div(className="row", children=[
        html.Div(className="col-12 col-lg-4", children=[
            html.H4("Precision-Recall Curve", className="mb-3"),
            pr_curve_component()
        ]),
        html.Div(className="col-12 col-lg-8", children=[
            html.H4("Eventos on-chain (últimos)", className="mb-3"),
            html.Div(className="d-flex gap-2 mb-2", children=[
                dcc.Input(id="search", type="text", placeholder="Buscar decision_id / tx_hash", className="form-control", style={"maxWidth":"360px"}),
                html.Button("Refresh", id="btn-refresh", n_clicks=0, className="btn btn-outline-primary"),
                dcc.Interval(id="auto-ivl", interval=10_000, n_intervals=0)
            ]),
            dash_table.DataTable(
                id="events-table",
                data=load_events().to_dict("records"),
                columns=[{"name":c, "id":c} for c in ["decision_id_hex","tx_ref_hash_hex","tx_hash","block_number"]],
                page_size=10,
                style_table={"overflowX":"auto", "maxHeight":"60vh", "overflowY":"auto"},
                style_header={"position":"sticky","top":"0","zIndex":1,"backgroundColor":"#f8f9fa","fontWeight":"600","border":"1px solid #dee2e6"},
                style_cell={"fontFamily":"Consolas, ui-monospace, Menlo, Monaco, 'Courier New', monospace","fontSize":"12px","whiteSpace":"nowrap","textOverflow":"ellipsis","maxWidth":"24ch","border":"1px solid #f1f3f5","padding":"6px"},
                style_data_conditional=[{"if":{"row_index":"odd"},"backgroundColor":"#fcfcfd"}]
            )
        ])
    ])
])

# ---------- callbacks ----------
@app.callback(
    Output("events-table","data"),
    Output("ts-badge","children"),
    Input("auto-ivl","n_intervals"),
    Input("btn-refresh","n_clicks"),
    Input("search","value"),
    prevent_initial_call=False
)
def refresh_events(_n, _c, q):
    df = load_events()
    if q and isinstance(q,str) and q.strip():
        ql = q.strip().lower()
        for col in ["decision_id_hex","tx_ref_hash_hex","tx_hash"]:
            if col in df.columns:
                df = df[df[col].astype(str).str.lower().str.contains(ql)]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return df.to_dict("records"), ts

@app.callback(
    Output("card-p95s","children"),
    Output("card-p95e","children"),
    Output("card-corr","children"),
    Input("auto-ivl","n_intervals"),
    Input("btn-refresh","n_clicks"),
    prevent_initial_call=False
)
def refresh_operational(_n, _c):
    e = load_e2e_summary() or {}
    p95s = e.get("p95_scoring_ms", 0.0)
    p95e = e.get("p95_e2e_ms", 0.0)
    corr = e.get("correlation_secure_to_event_pct", 0.0)
    return (
        kpi_card("p95 scoring (ms)", f"{p95s:.1f}"),
        kpi_card("p95 E2E (ms)", f"{p95e:.1f}"),
        kpi_card("Correlación secure→evento (%)", f"{corr:.1f}")
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
