# Partial eBay reserve-0 pilot

Two attempts were made to complete this two-auction pilot. Both stopped after state-log activity stalled. Their SQLite event logs are preserved as `partial_state.sqlite3` (attempt 1) and `partial_state_retry2.sqlite3` (attempt 2). No EDSL interview result file or completed settlement is claimed for either attempt.

Attempt 1: 73 events across two scopes; see `partial_state.sqlite3`.

Attempt 2: 78 events; per-scope event/read/write/version counts: `[('"auction-0000"', 46, 24, 22, 22), ('"auction-0001"', 32, 17, 15, 15)]`.
