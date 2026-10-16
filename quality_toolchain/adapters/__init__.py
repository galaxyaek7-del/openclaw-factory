# -*- coding: utf-8 -*-
"""Isolated per-tool adapters. Each adapter holds no policy and never writes
evidence or makes product decisions directly — it only computes a gate-shaped
result the runner/gate layer normalizes and records."""