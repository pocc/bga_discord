from bga_game_list import get_game_list_from_cache
from utils import simplify_name
import unittest


class TestUtils(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.games, errs = await get_game_list_from_cache()

    def test_simplify_name(self):
        # Exercise all of the existing simplifications rules:
        self.assertEqual(simplify_name("Gaïa"), "gaia")
        self.assertEqual(simplify_name("6  Nimmt!"), "sixnimmt")
        self.assertEqual(
            simplify_name("The Jelly Monster Lab"),
            "jellymonsterlab"
        )
        self.assertEqual(
            simplify_name("99 (trick-taking card game)"),
            "ninetynine"
        )
        self.assertEqual(
            simplify_name("Unconditional Surrender! World War 2 in Europe "),
            "unconditionalsurrender"
        )
        self.assertEqual(
            simplify_name("The Builders: Middle Ages"),
            "buildersmiddleages"
        )
        self.assertEqual(simplify_name("Through the Ages"), "throughtheages")
        self.assertEqual(
            simplify_name("Through the Ages: A new Story of Civilization"),
            "throughtheagesanewstoryofcivilization"
        )
        self.assertEqual(
            simplify_name("Marco Polo II: In the Service of the Khan"),
            "marcopolotwo"
        )
        self.assertEqual(
            simplify_name("The Voyages of Marco Polo"),
            "marcopolo"
        )
        self.assertEqual(
            simplify_name("The Werewolves of Miller's Hollow"),
            "werewolves"
        )
        self.assertEqual(simplify_name("Gear & Piston"), "gearandpiston")

        # Check for any collisions between simplified names:
        simplified_names = set()
        for full_name in self.games:
            simplified_name = simplify_name(full_name)
            self.assertNotIn(simplified_name, simplified_names)
            simplified_names.add(simplified_name)


if __name__ == '__main__':
    unittest.main()
