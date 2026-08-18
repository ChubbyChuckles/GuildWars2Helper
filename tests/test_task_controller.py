from __future__ import annotations

import time
import unittest
from unittest.mock import Mock, patch

from PyQt6 import QtCore

from gw2helper import constants
from gw2helper.controllers.task_controller import TaskController
from gw2helper.services.arcdps_telemetry import CombatTelemetrySnapshot
from gw2helper.services.gw2_api import BankSummary


class _CombatMonitor:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def snapshot(self) -> CombatTelemetrySnapshot:
        return CombatTelemetrySnapshot(
            bridge_status="ArcDPS BHud connected",
            character_loaded=True,
            skills=(),
            buffs=(),
        )


class BankSummaryControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])

    def test_loads_bank_summary_on_a_background_thread(self) -> None:
        summary = BankSummary(30, 12, 3, 2)
        client = Mock()
        client.get_bank_summary.return_value = summary
        controller = TaskController()
        received: list[BankSummary] = []
        controller.bank_summary_loaded.connect(received.append)

        with patch(
            "gw2helper.controllers.task_controller.Gw2ApiClient",
            return_value=client,
        ):
            self.assertTrue(controller.load_bank_summary())
            deadline = time.monotonic() + 1
            while not received and time.monotonic() < deadline:
                self._app.processEvents()
                time.sleep(0.01)

        self.assertEqual(received, [summary])
        client.get_bank_summary.assert_called_once_with()

    def test_rotation_starts_and_stops_with_current_cc_setting(self) -> None:
        controller = TaskController()
        started = []
        stopped = []

        def run_rotation(stop_event, telemetry_supplier, cc_supplier, update_status) -> None:
            del telemetry_supplier, update_status
            started.append(cc_supplier())
            stop_event.wait(1)

        controller.rotation_state_changed.connect(stopped.append)
        constants.set_combat_cc_enabled(True)
        with patch(
            "gw2helper.controllers.task_controller.tasks.do_condition_virtuoso_rotation",
            side_effect=run_rotation,
        ):
            self.assertTrue(controller.start_rotation())
            deadline = time.monotonic() + 1
            while not started and time.monotonic() < deadline:
                self._app.processEvents()
                time.sleep(0.01)
            self.assertEqual(started, [True])
            self.assertTrue(controller.is_rotation_active())
            self.assertTrue(controller.stop_rotation())
            deadline = time.monotonic() + 1
            while controller.is_rotation_active() and time.monotonic() < deadline:
                self._app.processEvents()
                time.sleep(0.01)

        self._app.processEvents()
        self.assertFalse(controller.is_rotation_active())
        self.assertIn(True, stopped)
        self.assertIn(False, stopped)
        constants.set_combat_cc_enabled(False)

    def test_controller_owns_combat_monitor_lifecycle(self) -> None:
        monitor = _CombatMonitor()
        controller = TaskController(combat_monitor=monitor)

        controller.start_combat_monitor()
        snapshot = controller.combat_telemetry_snapshot()
        controller.stop_combat_monitor()

        self.assertTrue(monitor.started)
        self.assertTrue(monitor.stopped)
        self.assertEqual(snapshot.bridge_status, "ArcDPS BHud connected")


if __name__ == "__main__":
    unittest.main()