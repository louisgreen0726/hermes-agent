# Louis Hermes Agent - Unreleased

Changes merged after `Louis-0.20.0.2` will be recorded here. The versioned
release record is [LOUIS_0.20.0.2.md](LOUIS_0.20.0.2.md).

## Pending

- The protected Louis updater now records whether the Gateway and Dashboard
  were running, stops both before dependency and checkout activation, and
  restarts each from the validated release with a PID stability check. Inactive
  services remain inactive, while a failed activation rolls back the source and
  restores both services to their prior running state.
