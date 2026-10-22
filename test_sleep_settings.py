import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sleep_settings


SCHEME = "381b4222-f694-41f0-9685-ff5bb260df2e"
OTHER_SCHEME = "a1841308-3541-4fab-bc81-f71556f20b4a"


class FakePowerCfg:
    def __init__(self):
        self.active = SCHEME
        self.values = {SCHEME: {"ac": 61, "dc": 2701}, OTHER_SCHEME: {"ac": 120, "dc": 180}}
        self.calls = []
        self.fail_on = None

    def __call__(self, *args, capture=False):
        self.calls.append(args)
        if args[0] == self.fail_on:
            raise subprocess.CalledProcessError(1, ["powercfg", *args])
        if args[0] == "/getactivescheme":
            return f"Power Scheme GUID: {self.active} (Balanced)"
        if args[0] == "/query":
            values = self.values[args[1]]
            return (
                f"Power Setting GUID: {sleep_settings.SLEEP_SETTING_GUID}\n"
                "Minimum Possible Setting: 0x00000000\n"
                "Maximum Possible Setting: 0xffffffff\n"
                f"現在の AC 電源設定インデックス: 0x{values['ac']:08x}\n"
                f"現在の DC 電源設定インデックス: 0x{values['dc']:08x}\n"
            )
        if args[0] in ("/setacvalueindex", "/setdcvalueindex"):
            self.values[args[1]]["ac" if args[0] == "/setacvalueindex" else "dc"] = int(args[4])
        return ""


class SleepTimeoutManagerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "snapshot.json"
        self.powercfg = FakePowerCfg()
        patcher = patch.object(sleep_settings, "_run_powercfg", side_effect=self.powercfg)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.manager = sleep_settings.SleepTimeoutManager(self.path)

    def test_read_exact_seconds_and_restore_across_instances(self):
        original = self.manager.read()
        self.assertEqual((original.ac_seconds, original.dc_seconds), (61, 2701))
        self.manager.set(ac_minutes=30)
        self.manager.set(dc_minutes=15)
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 1800, "dc": 900})
        self.assertEqual(self.manager.saved_snapshot(), original)

        another_instance = sleep_settings.SleepTimeoutManager(self.path)
        self.assertEqual(another_instance.restore(), original)
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 61, "dc": 2701})
        self.assertFalse(self.path.exists())

    def test_temporary_restores_when_body_raises(self):
        with self.assertRaisesRegex(RuntimeError, "job failed"):
            with self.manager.temporary(ac_minutes=0):
                self.assertEqual(self.powercfg.values[SCHEME]["ac"], 0)
                raise RuntimeError("job failed")
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 61, "dc": 2701})
        self.assertFalse(self.path.exists())

    def test_failed_restore_keeps_snapshot_for_retry(self):
        self.manager.set(ac_minutes=30, dc_minutes=15)
        self.powercfg.fail_on = "/setdcvalueindex"
        with self.assertRaises(subprocess.CalledProcessError):
            self.manager.restore()
        self.assertTrue(self.path.exists())
        self.powercfg.fail_on = None
        self.manager.restore()
        self.assertFalse(self.path.exists())

    def test_plan_switch_preserves_active_plan(self):
        self.manager.set(ac_minutes=30)
        self.powercfg.active = OTHER_SCHEME
        with self.assertRaises(RuntimeError):
            self.manager.set(dc_minutes=15)
        self.manager.restore()
        self.assertEqual(self.powercfg.active, OTHER_SCHEME)
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 61, "dc": 2701})

    def test_invalid_snapshot_and_arguments_do_not_modify_settings(self):
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid snapshot file"):
            self.manager.restore()
        self.path.write_text(json.dumps({"version": 1, "scheme_guid": SCHEME, "ac_seconds": -1, "dc_seconds": 0}))
        with self.assertRaises(ValueError):
            self.manager.set(ac_minutes=15)
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 61, "dc": 2701})
        self.path.unlink()
        with self.assertRaises(ValueError):
            self.manager.set(ac_minutes=True)
        self.assertFalse(self.path.exists())

    def test_temporary_rejects_pending_restore_point(self):
        self.manager.set(ac_minutes=30)
        with self.assertRaises(RuntimeError):
            with self.manager.temporary(dc_minutes=15):
                pass
        self.assertEqual(self.powercfg.values[SCHEME], {"ac": 1800, "dc": 2701})


if __name__ == "__main__":
    unittest.main()
