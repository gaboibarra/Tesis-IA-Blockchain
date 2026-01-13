# -*- coding: utf-8 -*-
"""
api/chain.py — Web3.py v6 EIP-1559
- Lee .env (RPC_URL, CHAIN_ID, PRIVATE_KEY, CONTRACT_ADDRESS)
- register_secure_tx(decision_id_hex, tx_ref_hash_hex) con firma local
- Reintentos y logs; idempotencia por decision_id en events.csv
- NUNCA imprime PRIVATE_KEY
"""

from __future__ import annotations
import json, os, time, csv, logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(ROOT, "logs")
ABI_DIR = os.path.join(ROOT, "abi")
EVENTS_CSV = os.path.join(ROOT, "events.csv")

os.makedirs(LOGS_DIR, exist_ok=True)

# --- logger ---
logger = logging.getLogger("fraudchain.chain")
logger.setLevel(logging.INFO)
_handler = RotatingFileHandler(os.path.join(LOGS_DIR, "chain.log"), maxBytes=2_000_000, backupCount=2, encoding="utf-8")
_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
_handler.setFormatter(_formatter)
logger.addHandler(_handler)

# --- env ---
load_dotenv(os.path.join(ROOT, ".env"))
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
CHAIN_ID = int(os.getenv("CHAIN_ID") or 1337)
PRIVATE_KEY = os.getenv("PRIVATE_KEY") or ""
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS") or ""

if not (PRIVATE_KEY.startswith("0x") and len(PRIVATE_KEY) == 66):
    raise RuntimeError("PRIVATE_KEY inválida. Debe empezar con 0x y tener 64 hex.")
if not (CONTRACT_ADDRESS.startswith("0x") and len(CONTRACT_ADDRESS) == 42):
    raise RuntimeError("CONTRACT_ADDRESS inválida. Asegúrate de haber hecho el deploy y actualizado .env.")

# --- web3 & contract ---
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 10}))
if not w3.is_connected():
    raise RuntimeError(f"No conecta a RPC_URL={RPC_URL}")

# Cargar ABI
with open(os.path.join(ABI_DIR, "TxRegistry.json"), "r", encoding="utf-8") as f:
    ABI = json.load(f)

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=ABI)

# --- cuenta local (NO imprimir nunca la clave) ---
account: LocalAccount = Account.from_key(PRIVATE_KEY)
SENDER = account.address

def _hex32(s: str) -> bytes:
    """
    Valida '0x' + 64 hex y devuelve bytes32
    """
    if not (isinstance(s, str) and s.startswith("0x") and len(s) == 66):
        raise ValueError("Debe ser hex de 32 bytes: '0x' + 64 hex.")
    return bytes.fromhex(s[2:])

def _already_recorded(decision_id_hex: str) -> bool:
    if not os.path.exists(EVENTS_CSV):
        return False
    with open(EVENTS_CSV, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("decision_id_hex") == decision_id_hex:
                return True
    return False

def _append_event(decision_id_hex: str, tx_ref_hash_hex: str, tx_hash: str, block_number: int) -> None:
    exists = os.path.exists(EVENTS_CSV)
    with open(EVENTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["decision_id_hex", "tx_ref_hash_hex", "tx_hash", "block_number"])
        if not exists:
            w.writeheader()
        w.writerow({
            "decision_id_hex": decision_id_hex,
            "tx_ref_hash_hex": tx_ref_hash_hex,
            "tx_hash": tx_hash,
            "block_number": block_number
        })

def _eip1559_fees() -> Dict[str,int]:
    """EIP-1559: fees conservadoras para Ganache."""
    # Ganache suele ignorar dinámica; valores estáticos conservadores
    base = w3.to_wei(20, "gwei")
    prio = w3.to_wei(2, "gwei")
    return {"maxFeePerGas": int(base), "maxPriorityFeePerGas": int(prio)}

def register_secure_tx(decision_id_hex: str, tx_ref_hash_hex: str, retries: int = 3, wait_sec: float = 1.5) -> Dict[str,Any]:
    """
    Envía una tx que emite el evento SecureTx(decisionId, txRefHash, ts).
    Idempotencia: si decision_id ya está en events.csv -> no envía.
    Retorna: {"tx_hash": "0x...", "blockNumber": N} o {"skipped": True}
    """
    # Validaciones
    d = _hex32(decision_id_hex)
    t = _hex32(tx_ref_hash_hex)

    if _already_recorded(decision_id_hex):
        msg = f"Decision {decision_id_hex} ya registrada; skip."
        logger.info(msg)
        return {"skipped": True, "reason": "already_recorded"}

    # Build tx
    nonce = w3.eth.get_transaction_count(SENDER)
    fees = _eip1559_fees()

    tx = contract.functions.registerSecureTx(d, t).build_transaction({
        "from": SENDER,
        "nonce": nonce,
        "chainId": CHAIN_ID,
        "type": 2,  # EIP-1559
        **fees,
        # Gas estimado con colchón
        "gas": int(contract.functions.registerSecureTx(d, t).estimate_gas({"from": SENDER}) * 1.2),
    })

    # Intentar con reintentos en errores típicos
    last_err: Optional[Exception] = None
    for attempt in range(1, retries+1):
        try:
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            txh = tx_hash.hex()
            bn  = int(receipt["blockNumber"])
            _append_event(decision_id_hex, tx_ref_hash_hex, txh, bn)
            logger.info(f"EVENT OK | decision_id={decision_id_hex} txRefHash={tx_ref_hash_hex} tx_hash={txh} block={bn}")
            return {"tx_hash": txh, "blockNumber": bn}
        except Exception as e:
            last_err = e
            logger.warning(f"TX attempt {attempt}/{retries} failed: {e}")
            time.sleep(wait_sec)
            # Actualizar nonce por si se consumió
            nonce = w3.eth.get_transaction_count(SENDER)
            tx["nonce"] = nonce

    logger.error(f"TX permanent failure for decision_id={decision_id_hex}: {last_err}")
    raise RuntimeError(f"TX failed after {retries} attempts: {last_err}")
