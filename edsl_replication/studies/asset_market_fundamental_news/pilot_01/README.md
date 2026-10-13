# Pilot 01 status

These artifacts are retained for audit. The positive arm completed, but its
period-5 payoff update was recorded as a no-op because the machine's guard
checked for period 5 after settlement had advanced state to period 6. It did
not receive the positive treatment and is excluded from analysis. The negative
and control specifications were prepared with the same guard version and were
not run. Use the corrected specifications in `../pilot_02/`.
