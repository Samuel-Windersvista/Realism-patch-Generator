import unittest
from pathlib import Path

from generate_realism_patch import RealismPatchGenerator


BASE_DIR = Path(__file__).resolve().parents[1]


class AmmoRuleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = RealismPatchGenerator(str(BASE_DIR))

    def _ammo_info(self, properties=None):
        return {
            "item_id": "synthetic-ammo",
            "parent_id": "5485a8684bdc2da71d8b4567",
            "clone_id": None,
            "template_id": None,
            "template_file": "ammoTemplates.json",
            "name": None,
            "is_weapon": False,
            "is_gear": False,
            "is_consumable": False,
            "item_type": "RealismMod.Ammo, RealismMod",
            "properties": properties or {},
            "source_file": "synthetic.json",
            "format_type": "CURRENT_PATCH",
        }

    def test_infer_12g_profile_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "patron_12x70_buckshot",
        }

        self.assertEqual("shotgun_12g", self.generator._infer_ammo_profile(patch, self._ammo_info()))

    def test_infer_20g_profile_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "patron_20x70_ap",
        }

        self.assertEqual("shotgun_20g", self.generator._infer_ammo_profile(patch, self._ammo_info()))

    def test_infer_23x75_profile_from_name(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "patron_23x75_shrapnel_10",
        }

        self.assertEqual("shotgun_23x75", self.generator._infer_ammo_profile(patch, self._ammo_info()))

    def test_fallback_unknown_shotgun_payload_to_shotgun_shell(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "mod_shell_flechette_custom",
        }

        self.assertEqual("shotgun_shell", self.generator._infer_ammo_profile(patch, self._ammo_info()))

    def test_apply_20g_rules_generates_values_inside_new_ranges(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "patron_20x70_buckshot",
            "PenetrationPower": 12,
        }

        self.generator.apply_realism_sanity_check(patch, self._ammo_info())

        self.assertGreaterEqual(float(patch["InitialSpeed"]), 300.0)
        self.assertLessEqual(float(patch["InitialSpeed"]), 520.0)
        self.assertGreaterEqual(float(patch["BulletMassGram"]), 18.0)
        self.assertLessEqual(float(patch["BulletMassGram"]), 36.5)
        self.assertGreaterEqual(float(patch["ammoRec"]), 4.0)
        self.assertLessEqual(float(patch["ammoRec"]), 38.0)

    def test_low_penetration_shotgun_round_stays_above_one_pen(self) -> None:
        patch = {
            "$type": "RealismMod.Ammo, RealismMod",
            "Name": "patron_23x75_shrapnel_10",
            "PenetrationPower": 6,
        }

        self.generator.apply_realism_sanity_check(patch, self._ammo_info())

        self.assertGreaterEqual(float(patch["PenetrationPower"]), 1.0)


if __name__ == "__main__":
    unittest.main()