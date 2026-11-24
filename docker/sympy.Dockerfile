# SymPy engine image (F-05.01). Runs only inside mathlab.sandbox: no network, read-only root.
FROM python:3.12.12-slim-bookworm
RUN pip install --no-cache-dir sympy==1.13.3 mpmath==1.3.0
USER 65534:65534
