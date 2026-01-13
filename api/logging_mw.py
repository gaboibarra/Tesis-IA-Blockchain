# -*- coding: utf-8 -*-
"""
api/logging_mw.py — middleware de logging para Flask (se usará en Paso 8)
"""
import time, logging
from typing import Callable
from flask import request

def request_logger(app):
    logger = logging.getLogger("fraudchain.api")
    logger.setLevel(logging.INFO)

    @app.before_request
    def _before():
        request.start_ts = time.perf_counter()

    @app.after_request
    def _after(resp):
        try:
            dt = (time.perf_counter() - getattr(request, "start_ts", time.perf_counter()))*1000.0
            logger.info(f"{request.method} {request.path} {resp.status_code} {dt:.1f}ms")
        except Exception:
            pass
        return resp

    return app
