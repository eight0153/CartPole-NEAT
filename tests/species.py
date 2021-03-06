"""Unit tests for the name generation module."""
import json
import random
import unittest

from neat.creature import Creature
from neat.species import Species


class SpeciesUnitTest(unittest.TestCase):
    def test_json(self):
        """Test whether a species can be saved to and loaded from JSON."""
        species = Species()
        species.assign_members([Creature(4, 1) for _ in range(100)])
        species.allotted_offspring_quota = 93

        dump = json.dumps(species.to_json())
        species_load = Species.from_json(json.loads(dump))

        self.assertEqual(len(species), len(species_load))
        self.assertTrue(species.representative
                        .distance(species_load.representative) < 1e-8)
        self.assertEqual(species.name, species_load.name)
        self.assertEqual(species.id, species_load.id)
        self.assertEqual(species.allotted_offspring_quota,
                         species_load.allotted_offspring_quota)
        self.assertTrue(species.champion
                        .distance(species_load.champion) < 1e-8)


if __name__ == '__main__':
    random.seed(42)

    unittest.main()
