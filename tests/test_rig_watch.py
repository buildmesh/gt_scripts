import subprocess
import unittest
from unittest.mock import call, patch

import rig_watch


RIG_LIST_SAMPLE = [
    {
        "name": "env4ai",
        "status": "operational",
        "witness": "running",
        "refinery": "running",
        "polecats": 2,
        "crew": 1,
    },
    {
        "name": "FoodMesh",
        "status": "operational",
        "witness": "stopped",
        "refinery": "stopped",
        "polecats": 0,
        "crew": 0,
    },
]

RIG_STATUS_ENV4AI_WITH_DONE = """env4ai
  Status: OPERATIONAL
  Path: /home/ubuntu/gt/env4ai
  Beads prefix: en-

Witness
  ● running

Refinery
  ● running

Polecats (1)
  ● furiosa: working → en-1jo.5
  ○ slit: done → en-1jo.4

Crew (1)
  ● env4ai: main (dirty)
"""

RIG_STATUS_ENV4AI_NO_DONE = """env4ai
  Status: OPERATIONAL
  Path: /home/ubuntu/gt/env4ai
  Beads prefix: en-

Witness
  ● running

Refinery
  ● running

Polecats (1)
  ● furiosa: working → en-1jo.5

Crew (1)
  ● env4ai: main (dirty)
"""

RIG_STATUS_FOODMESH = """FoodMesh
  Status: OPERATIONAL

Witness
  ● stopped

Refinery
  ● stopped

Polecats (0)

Crew (0)
"""


class TestHasDonePolecat(unittest.TestCase):
    def test_detects_done_in_sample_polecats_section(self):
        self.assertTrue(rig_watch.has_done_polecat(RIG_STATUS_ENV4AI_WITH_DONE))

    def test_returns_false_when_polecats_have_no_done_status(self):
        self.assertFalse(rig_watch.has_done_polecat(RIG_STATUS_ENV4AI_NO_DONE))


class TestLoopOnce(unittest.TestCase):
    @patch("rig_watch.run_command")
    @patch("rig_watch.run_text_command")
    @patch("rig_watch.run_json_command")
    def test_done_polecat_nudges_witness_and_non_empty_mq_nudges_refinery(
        self, mock_run_json, mock_run_text, mock_run_command
    ):
        mock_run_json.side_effect = [
            RIG_LIST_SAMPLE,
            [
                {
                    "id": "en-wisp-bh8mc",
                    "title": "Merge: en-1jo.5",
                    "status": "open",
                }
            ],
            None,
        ]
        mock_run_text.side_effect = [
            RIG_STATUS_ENV4AI_WITH_DONE,
            RIG_STATUS_FOODMESH,
        ]

        rig_watch.loop_once(iteration=1)

        self.assertEqual(
            mock_run_command.call_args_list,
            [
                call(
                    [
                        "gt",
                        "nudge",
                        "env4ai/witness",
                        "-m",
                        "Please check on stale polecats and 'gt done' them",
                    ],
                    "nudge witness for env4ai",
                ),
                call(
                    [
                        "gt",
                        "nudge",
                        "env4ai/refinery",
                        "-m",
                        "Please process merge queue. Merge conflicts should result in a bead to resolve the merge conflict",
                    ],
                    "nudge refinery for env4ai",
                ),
            ],
        )

    @patch("rig_watch.run_command")
    @patch("rig_watch.run_text_command")
    @patch("rig_watch.run_json_command")
    @patch("rig_watch.print")
    def test_periodic_health_nudge_runs_for_each_operational_rig_every_five_iterations(
        self, mock_print, mock_run_json, mock_run_text, mock_run_command
    ):
        mock_run_json.side_effect = [
            RIG_LIST_SAMPLE,
            None,
            None,
        ]
        mock_run_text.side_effect = [
            RIG_STATUS_ENV4AI_NO_DONE,
            RIG_STATUS_FOODMESH,
        ]

        rig_watch.loop_once(iteration=5)

        self.assertEqual(
            mock_run_command.call_args_list,
            [
                call(
                    [
                        "gt",
                        "nudge",
                        "env4ai/witness",
                        "-m",
                        "Please check on all working polecats and make sure they aren't stuck or nonresponsive",
                    ],
                    "periodic witness health nudge for env4ai",
                ),
                call(
                    [
                        "gt",
                        "nudge",
                        "FoodMesh/witness",
                        "-m",
                        "Please check on all working polecats and make sure they aren't stuck or nonresponsive",
                    ],
                    "periodic witness health nudge for FoodMesh",
                ),
            ],
        )
        self.assertEqual(mock_print.call_count, 2)

    @patch("rig_watch.run_command")
    @patch("rig_watch.run_text_command")
    @patch("rig_watch.run_json_command")
    def test_skips_non_operational_rigs(self, mock_run_json, mock_run_text, mock_run_command):
        mock_run_json.return_value = [
            {"name": "env4ai", "status": "offline"},
            {"name": "env5ai", "status": "degraded"},
        ]

        rig_watch.loop_once(iteration=10)

        mock_run_text.assert_not_called()
        mock_run_command.assert_not_called()


class TestJsonCommandBehavior(unittest.TestCase):
    @patch("rig_watch.log_command")
    @patch("rig_watch.subprocess.run")
    def test_run_json_command_parses_null_as_none(self, mock_subprocess_run, mock_log_command):
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["gt", "mq", "list", "env4ai", "--json"],
            returncode=0,
            stdout="null\n",
            stderr="",
        )

        result = rig_watch.run_json_command(
            ["gt", "mq", "list", "env4ai", "--json"],
            "gt mq list env4ai --json",
        )

        self.assertIsNone(result)
        mock_log_command.assert_called_once_with(["gt", "mq", "list", "env4ai", "--json"])


class TestLogging(unittest.TestCase):
    @patch("rig_watch.print")
    @patch("rig_watch.timestamp", return_value="2026-03-02 12:00:00")
    def test_log_command_prints_timestamp_and_command(self, mock_timestamp, mock_print):
        rig_watch.log_command(["gt", "mq", "list", "env4ai", "--json"])

        mock_timestamp.assert_called_once_with()
        mock_print.assert_called_once_with(
            "[2026-03-02 12:00:00] gt mq list env4ai --json"
        )


if __name__ == "__main__":
    unittest.main()
