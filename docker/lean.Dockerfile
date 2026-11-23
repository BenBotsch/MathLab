# Lean engine image (F-00.04). Lean is pinned by lean/lean-toolchain, Mathlib by
# lean/lake-manifest.json. The Mathlib build cache is downloaded at image build time.
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
CMD ["lake", "env", "lean", "--version"]
