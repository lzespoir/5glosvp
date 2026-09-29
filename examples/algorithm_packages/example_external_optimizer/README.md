# ExampleExternalOptimizer

This is the Day 10 trusted external Python V0.1 example package.

It contains `algorithm.yaml`, `optimizer.py`, and an optional `requirements.txt`. The
platform imports it only from a local workspace directory, validates the manifest and
SDK interface, runs a lightweight fake smoke test, and then owns the real simulation
evaluation, KPI calculation, constraints, trace, and evidence.

The package does not access Sionna, the backend, or simulator objects. It only suggests
candidate association vectors through the canonical Algorithm SDK. Validation and the
benchmark result are integration evidence, not a claim of algorithm correctness or
paper reproduction.
