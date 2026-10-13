"""Deterministic conformance tests for the pure EDSL market Machine.

Run from this directory with:
    python3 -m unittest -v test_machine_conformance.py

The small reference calculations below intentionally use ordinary Python and
are separate from the Machine expression builders.
"""

from __future__ import annotations

import unittest

from edsl.sharedstate import ExecutionLimits, Runtime

from machine_definition import TRADERS, build_machine


SEED = 153101


def decision(side: str = "hold", price_cents: int = 0, quantity: int = 0):
    return {"side": side, "price_cents": price_cents, "quantity": quantity}


class MachineConformanceTests(unittest.TestCase):
    def setUp(self):
        self.machine = build_machine(seed=SEED)
        self.runtime = Runtime(limits=ExecutionLimits(max_steps=10_000_000))
        self.state = self.runtime.initial_state(self.machine)

    def execute(self, state, command, **inputs):
        return self.runtime.execute(self.machine, state, command, inputs)

    def submit_all_holds(self, state, period=1):
        for trader in TRADERS:
            result = self.execute(
                state,
                "submit_order",
                trader=trader,
                period=period,
                decision=decision(),
            )
            self.assertEqual(result.event["status"], "applied")
            state = result.state
        return state

    def submit_order(self, state, trader, side, price, quantity, period=1):
        return self.execute(
            state,
            "submit_order",
            trader=trader,
            period=period,
            decision=decision(side, price, quantity),
        )

    def test_command_preconditions_reject_wrong_phase_duplicate_and_unknown_trader(self):
        # Clearing before all 12 orders is a no-op and preserves state.
        early_clear = self.execute(self.state, "clear_orders", period=1)
        self.assertEqual(early_clear.event["status"], "noop")
        self.assertEqual(early_clear.state, self.state)
        early_settlement = self.execute(self.state, "settle", period=1)
        self.assertEqual(early_settlement.event["status"], "noop")
        self.assertEqual(early_settlement.state, self.state)

        first = self.submit_order(self.state, TRADERS[0], "hold", 0, 0)
        self.assertEqual(first.event["status"], "applied")
        duplicate = self.submit_order(first.state, TRADERS[0], "hold", 0, 0)
        self.assertEqual(duplicate.event["status"], "noop")
        self.assertEqual(duplicate.state, first.state)

        unknown = self.submit_order(first.state, "not-a-trader", "hold", 0, 0)
        self.assertEqual(unknown.event["status"], "noop")
        self.assertEqual(unknown.state, first.state)

        wrong_period = self.submit_order(first.state, TRADERS[1], "hold", 0, 0, period=2)
        self.assertEqual(wrong_period.event["status"], "noop")
        self.assertEqual(wrong_period.state, first.state)

    def test_admission_caps_buy_by_cash_and_sell_by_inventory(self):
        state = {**self.state, "accounts": dict(self.state["accounts"])}
        state["accounts"][TRADERS[0]] = {
            **state["accounts"][TRADERS[0]], "cash_cents": 250
        }
        state["accounts"][TRADERS[1]] = {
            **state["accounts"][TRADERS[1]], "shares": 2
        }

        buy = self.submit_order(state, TRADERS[0], "buy", 100, 4)
        sell = self.submit_order(buy.state, TRADERS[1], "sell", 100, 5)
        self.assertEqual(buy.state["orders"][TRADERS[0]]["accepted_quantity"], 2)
        self.assertEqual(sell.state["orders"][TRADERS[1]]["accepted_quantity"], 2)

    def test_invalid_order_is_recorded_but_admits_no_units(self):
        invalid = self.submit_order(self.state, TRADERS[0], "buy", 0, 1)
        order = invalid.state["orders"][TRADERS[0]]
        self.assertEqual(order["accepted_quantity"], 0)
        self.assertEqual(order["rejection"], "invalid order")

    def test_no_crossing_orders_produce_zero_volume_and_keep_reference_price(self):
        state = self.state
        for index, trader in enumerate(TRADERS):
            if index == 0:
                side, price, qty = "buy", 1000, 1
            elif index == 1:
                side, price, qty = "sell", 1200, 1
            else:
                side, price, qty = "hold", 0, 0
            state = self.submit_order(state, trader, side, price, qty).state

        cleared = self.execute(state, "clear_orders", period=1)
        self.assertEqual(cleared.event["status"], "applied")
        self.assertEqual(cleared.state["clearing"]["volume"], 0)
        settled = self.execute(cleared.state, "settle", period=1)
        self.assertEqual(settled.event["status"], "applied")
        self.assertIsNone(settled.state["tape"][0]["price"])
        self.assertEqual(settled.state["last_price_cents"], 1400)
        self.assertEqual(settled.state["orders"], {})
        self.assertIsNone(settled.state["clearing"])

    def test_crossing_match_uses_seeded_priority_and_midpoint_half_up(self):
        # Two tied buyers compete for one unit. The seed schedule says which
        # trader has priority; a 1001-cent bid and 1000-cent ask imply 1001 cents.
        priorities = self.machine.constants["priority_schedule"][0]
        tied_buyers = [TRADERS[0], TRADERS[2]]
        expected_winner = min(tied_buyers, key=priorities.__getitem__)
        loser = next(trader for trader in tied_buyers if trader != expected_winner)

        state = self.state
        orders = {
            TRADERS[0]: ("buy", 1001, 1),
            TRADERS[2]: ("buy", 1001, 1),
            TRADERS[1]: ("sell", 1000, 1),
        }
        for trader in TRADERS:
            side, price, qty = orders.get(trader, ("hold", 0, 0))
            state = self.submit_order(state, trader, side, price, qty).state

        cleared = self.execute(state, "clear_orders", period=1)
        clearing = cleared.state["clearing"]
        self.assertEqual(clearing["volume"], 1)
        self.assertEqual(clearing["price_cents"], (1001 + 1000 + 1) // 2)
        self.assertEqual(clearing["buy_fills"], {expected_winner: 1})
        self.assertEqual(clearing["sell_fills"], {TRADERS[1]: 1})
        self.assertNotIn(loser, clearing["buy_fills"])

        # Independent settlement reference: trade at 1001 cents, then rounded
        # 5% interest, then the first-period $1 dividend on post-trade shares.
        dividend = self.machine.constants["dividend_schedule"][0]
        self.assertEqual(dividend, 100)
        settled = self.execute(cleared.state, "settle", period=1).state
        buyer = settled["accounts"][expected_winner]
        seller = settled["accounts"][TRADERS[1]]
        buyer_cash_after_trade = 10_000 - 1001
        buyer_interest = (buyer_cash_after_trade * 5 + 50) // 100
        expected_buyer_cash = buyer_cash_after_trade + buyer_interest + 5 * dividend
        seller_cash_after_trade = 10_000 + 1001
        seller_interest = (seller_cash_after_trade * 5 + 50) // 100
        expected_seller_cash = seller_cash_after_trade + seller_interest + 3 * dividend
        self.assertEqual(buyer["cash_cents"], expected_buyer_cash)
        self.assertEqual(buyer["shares"], 5)
        self.assertEqual(seller["cash_cents"], expected_seller_cash)
        self.assertEqual(seller["shares"], 3)
        self.assertEqual(buyer["history"][0]["fill"], 1)
        self.assertEqual(seller["history"][0]["fill"], -1)
        self.assertEqual(sum(a["shares"] for a in settled["accounts"].values()), 48)
        self.assertEqual(settled["period"], 2)
        self.assertEqual(settled["last_price_cents"], 1001)

    def test_multi_unit_clearing_matches_maximal_crossing_quantity(self):
        state = self.state
        orders = {
            TRADERS[0]: ("buy", 1500, 2),
            TRADERS[1]: ("sell", 1400, 1),
            TRADERS[2]: ("sell", 1450, 1),
        }
        for trader in TRADERS:
            side, price, qty = orders.get(trader, ("hold", 0, 0))
            state = self.submit_order(state, trader, side, price, qty).state

        cleared = self.execute(state, "clear_orders", period=1).state
        clearing = cleared["clearing"]
        self.assertEqual(clearing["volume"], 2)
        # The marginal matched bid is 1500 and the marginal ask is 1450.
        self.assertEqual(clearing["price_cents"], (1500 + 1450 + 1) // 2)
        self.assertEqual(clearing["buy_fills"], {TRADERS[0]: 2})
        self.assertEqual(clearing["sell_fills"], {TRADERS[1]: 1, TRADERS[2]: 1})

    def test_exact_half_cent_interest_rounds_up(self):
        state = {**self.state, "accounts": dict(self.state["accounts"])}
        state["accounts"][TRADERS[0]] = {
            **state["accounts"][TRADERS[0]], "cash_cents": 10, "shares": 0
        }
        state = self.submit_all_holds(state)
        cleared = self.execute(state, "clear_orders", period=1).state
        settled = self.execute(cleared, "settle", period=1).state
        account = settled["accounts"][TRADERS[0]]
        # 5% of 10 cents is exactly half a cent; half-up gives 1 cent.
        self.assertEqual(account["history"][0]["interest_cents"], 1)
        self.assertEqual(account["cash_cents"], 11)

    def test_terminal_settlement_redeems_every_share_and_rejects_more_orders(self):
        state = {**self.state, "period": 30}
        state = self.submit_all_holds(state, period=30)
        cleared = self.execute(state, "clear_orders", period=30)
        settled = self.execute(cleared.state, "settle", period=30)

        self.assertTrue(settled.state["finished"])
        self.assertEqual(settled.state["period"], 31)
        self.assertEqual(settled.state["orders"], {})
        self.assertIsNone(settled.state["clearing"])
        self.assertEqual(sum(a["shares"] for a in settled.state["accounts"].values()), 0)
        self.assertEqual(
            sum(a["redeemed_shares"] for a in settled.state["accounts"].values()), 48
        )

        # This seed's final dividend is $1; with no trades, one account receives
        # $5 interest, $4 dividend, and $56 redemption on top of $100 cash.
        first_account = settled.state["accounts"][TRADERS[0]]
        self.assertEqual(self.machine.constants["dividend_schedule"][29], 100)
        self.assertEqual(first_account["cash_cents"], 16_500)
        rejected = self.submit_order(
            settled.state, TRADERS[0], "buy", 100, 1, period=31
        )
        self.assertEqual(rejected.event["status"], "noop")
        self.assertEqual(rejected.state, settled.state)


if __name__ == "__main__":
    unittest.main()
