# Lean engine image (F-00.04). Lean is pinned by lean/lean-toolchain, Mathlib by
# lean/lake-manifest.json. The Mathlib build cache is downloaded at image build time.
# The Lean REPL (ADR-0002, F-04.02) is built at the tag matching the toolchain.
FROM debian:bookworm-20251208-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 lean
USER lean
ENV ELAN_HOME=/home/lean/.elan PATH=/home/lean/.elan/bin:$PATH
RUN curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --no-modify-path --default-toolchain none
WORKDIR /home/lean/project
COPY --chown=lean:lean lean/ ./
RUN lake exe cache get && lake build
# leanprover-community/repl, tag v4.36.0. Must move together with lean/lean-toolchain.
ARG REPL_REV=1b9fdf8ab81e52ba8651207c07e405129de2ffbe
RUN git clone https://github.com/leanprover-community/repl.git /home/lean/tools/repl \
    && git -C /home/lean/tools/repl checkout --detach "$REPL_REV" \
    && cp lean-toolchain /home/lean/tools/repl/lean-toolchain \
    && cd /home/lean/tools/repl && lake build repl
CMD ["lake", "env", "lean", "--version"]
