from __future__ import annotations

import unittest

from gw2helper import persistence


class EmptyingScheduleTests(unittest.TestCase):
    def test_emptying_becomes_due_after_seven_distinct_farming_days(self) -> None:
        state = persistence.AppState()

        for day in range(1, persistence.EMPTY_AFTER_FARM_DAYS + 1):
            self.assertTrue(persistence.record_farming_day(state, f"2026-08-{day:02}"))

        self.assertFalse(persistence.record_farming_day(state, "2026-08-07"))
        self.assertTrue(persistence.is_emptying_due(state))
        self.assertEqual(
            persistence.farming_days_since_empty_count(state),
            persistence.EMPTY_AFTER_FARM_DAYS,
        )

    def test_emptying_resets_cycle_counts_but_keeps_character_history(self) -> None:
        state = persistence.AppState(farm_count_since_empty=3)
        persistence.record_farming_day(state, "2026-08-01")
        persistence.record_character_farmed(state, "Brooke Kensington")
        persistence.record_character_farmed(state, "Brooke Kensington")

        persistence.complete_emptying_cycle(state, "2026-08-08T10:00:00Z")

        self.assertEqual(state.last_empty_timestamp, "2026-08-08T10:00:00Z")
        self.assertEqual(state.farm_count_since_empty, 0)
        self.assertEqual(state.farming_days_since_empty, [])
        self.assertEqual(state.character_farm_counts_since_empty, {})
        self.assertEqual(state.character_farm_counts, {"Brooke Kensington": 2})

    def test_schedule_data_round_trips_through_json_state(self) -> None:
        state = persistence.AppState()
        persistence.record_farming_day(state, "2026-08-01")
        persistence.record_character_farmed(state, "Haylene Blackfyre")

        restored = persistence.AppState.from_dict(state.to_dict())

        self.assertEqual(restored.farming_days_since_empty, ["2026-08-01"])
        self.assertEqual(restored.character_farm_counts, {"Haylene Blackfyre": 1})
        self.assertEqual(
            restored.character_farm_counts_since_empty,
            {"Haylene Blackfyre": 1},
        )

    def test_emptied_character_is_retained_in_history_not_new_cycle(self) -> None:
        state = persistence.AppState()

        persistence.record_character_farmed(
            state,
            "Brooke Kensington",
            count_toward_current_cycle=False,
        )

        self.assertEqual(state.character_farm_counts, {"Brooke Kensington": 1})
        self.assertEqual(state.character_farm_counts_since_empty, {})


if __name__ == "__main__":
    unittest.main()