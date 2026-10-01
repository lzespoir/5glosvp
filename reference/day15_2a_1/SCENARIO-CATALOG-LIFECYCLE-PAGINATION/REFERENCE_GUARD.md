# Reference guard

`WorkspaceService.delete_scenario()` calls the extensible `ScenarioReferenceGuard` before unlinking the scenario definition.

Currently registered authoritative provider:

- `scenario_instances`: scans the workspace's immutable ScenarioInstance collection for the scenario ID.

Provider registration is explicit through `register_provider(name, provider)`. A nonzero summary blocks deletion with HTTP 409. The guard performs no cascade operation; tests assert both the definition and reference remain after rejection.

The current ConfiguredScenario model is not yet joined to Experiment, Comparison, Evidence, AcceptanceScenarioSet, Artifact, or Verification IDs. Those producers must register providers when Day15.2B establishes their authoritative relationships. The implementation does not pretend these unconnected objects are checked.
