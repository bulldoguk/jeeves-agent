# Changelog

## 0.1.0

- Initial skeleton: connects to Home Assistant, polls watched entities for
  staleness (no updates within threshold), tracks open issues in SQLite,
  and raises/clears notifications via the configured `notify` service.
- This is a walking skeleton — temperature-baseline learning, camera
  event-rate comparison, system-health, and update checks are not yet
  implemented (see SPEC.md in the project knowledge base).
