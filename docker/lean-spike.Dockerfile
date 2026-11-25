# Spike image for the Lean interaction layer (F-04.11, ADR-0002). Not part of the runtime.
# Builds the Lean REPL at its v4.36.0 tag against the pinned toolchain of mathlab-lean.
# Pantograph (dev 6479c9bb, toolchain v4.35.0) does not build with v4.36.0: missing match case
# Info.ofChoiceResolutionInfo and the removed Lean.mkTheoremValEx and
# Lean.mkReducibilityHintsRegularEx. See ADR-0002, so it is not part of this image.
FROM mathlab-lean:latest
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends time \
    && rm -rf /var/lib/apt/lists/*
USER lean
WORKDIR /home/lean/tools
ARG REPL_REV=1b9fdf8ab81e52ba8651207c07e405129de2ffbe
RUN git clone https://github.com/leanprover-community/repl.git \
    && git -C repl checkout --detach "$REPL_REV" \
    && cp /home/lean/project/lean-toolchain repl/lean-toolchain \
    && cd repl && lake build repl
WORKDIR /home/lean/project
