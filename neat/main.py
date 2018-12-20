"""Implements the NEAT algorithm."""

from time import time

import numpy as np
from gym import wrappers

from neat.creature import Creature
from neat.species import Species


class NeatAlgorithm:
    """An implementation of the NEAT algorithm based off the original paper."""

    # Percentage of each species that is allowed to reproduce.
    survival_threshold = 0.3

    def __init__(self, env, n_pops=150):
        self.env = env
        self.n_pops = n_pops
        self.population = self.init_population(env.observation_space.shape[0],
                                               env.action_space.n)
        self.species = set()

    def init_population(self, n_inputs, n_outputs):
        """Create a population of n individuals.

        Each individual is initially has a fully connected neural network with
        n_inputs neurons in the input layer and n_outputs neurons in the
        output layer.

        Arguments:
            n_inputs: How many inputs to expect. An observation in CartPole
                      has four dimensions, so in this case n_inputs would be
                      four.
            n_outputs: How many outputs to expect. CartPole has two actions in
                      its action space, so in this case n_inputs would be two.

        Returns: the initialised population that is ready for use.
        """
        creature = Creature(n_inputs, n_outputs)
        population = [creature.copy() for _ in range(self.n_pops)]

        return population

    def train(self, n_episodes=100, n_steps=200, debug_mode=False):
        """Train species of individuals.

        Arguments:
            n_episodes: The number of episodes to trian for.
            n_steps: The maximum number of steps per individual per episode.
            debug_mode: If set to True, some features that aren't intended for
                        testing environments and such are disabled.
        """
        sim_start = time()

        step_msg_format = \
            "\r{:03d}/{:03d} - steps: {:02d} - step time {:02.4f}s"

        episode_complete_msg_format = "\r{:03d}/{:03d} - " \
                                      "mean steps: {:.2f} - " \
                                      "median steps: {:.2f} - " \
                                      "avg. step time: {:02.4f}s - " \
                                      "total time: {:.4f}s"

        step_history = [[] for _ in range(n_episodes)]

        for episode in range(n_episodes):
            episode_start = time()

            print('Episode {:02d}/{:02d}'.format(episode + 1, n_episodes))

            for pop_i, creature in enumerate(self.population):
                observation = self.env.reset()
                pop_start = time()

                for step in range(n_steps):
                    action = creature.get_action(observation)
                    observation, reward, done, _ = self.env.step(action)

                    if done:
                        creature.fitness = step + 1
                        step_history[episode].append(step + 1)

                        break
                else:
                    creature.fitness = n_steps

                print(step_msg_format.format(pop_i + 1, self.n_pops,
                                             step_history[episode][-1],
                                             time() - pop_start),
                      end='')

            self.do_the_thing()

            mean_steps = np.mean(step_history[episode])
            median_steps = np.median(step_history[episode])
            total_episode_time = time() - episode_start
            avg_step_time = total_episode_time / self.n_pops

            print(episode_complete_msg_format.format(self.n_pops, self.n_pops,
                                                     mean_steps, median_steps,
                                                     avg_step_time,
                                                     total_episode_time))

        print('Total run time: {:.2f}s - avg. steps: {:.2f} - best steps: {}'
              .format(time() - sim_start, np.mean(step_history),
                      np.max(step_history)))
        print()

        if not debug_mode:
            self.post_training_stuff()

    def post_training_stuff(self):
        """Do post training stuff."""
        print('Here are the species that made it to the end and the number of '
              'creatures in each of them:')

        for species in self.species:
            print('%s - %d creatures.' % (species, len(species)))

        best_species = max(self.species, key=lambda s: s.champion.fitness)
        print('Out of these species, the best species was %s.' % best_species)

        print('The overall champion was a creature with %d nodes and %d '
              'connections in its neural network.' %
              (len(best_species.champion.genotype.node_genes),
               len(best_species.champion.genotype.connection_genes)))

        self.record_video(best_species.champion)

        self.env.close()

    def record_video(self, creature):
        """Record a video of the creature trying to solve the problem.

        Arguments:
            creature: the creature to record.
        """
        print("Recording fittest creature.")

        env = wrappers.Monitor(self.env, './data/videos/%s' % time())

        for i_episode in range(20):
            observation = env.reset()

            for step in range(200):
                env.render()

                action = creature.get_action(observation)
                observation, _, done, _ = env.step(action)

                if done:
                    print("Episode finished after {} timesteps".format(step + 1))
                    break

    def do_the_thing(self):
        """Do the post-episode stuff such as speciating, adjusting creature
        fitness, crossover etc.
        """
        for creature in self.population:
            self.speciate(creature)

        for creature in self.population:
            creature.adjust_fitness()

        self.allot_offspring_quota()
        self.not_so_natural_selection()
        self.mating_season()

    def speciate(self, creature):
        """Place a creature into a species, or create a new species if no
        suitable species exists.

        Arguments:
            creature: the creature to place into a species.
        """
        for species_i in self.species:
            if creature.distance(species_i.representative) < \
                    Species.compatibility_threshold:
                species_i.add(creature)
                creature.species = species_i

                break
        else:
            new_species = Species()
            new_species.add(creature)
            new_species.representative = creature

            self.species.add(new_species)
            creature.species = new_species

    def allot_offspring_quota(self):
        """Allot the number of offspring each species is allowed for the
        current generation.

        Sort of like the One-Child policy but we force each species to have
        exactly the amount of babies we tell them to. No more, no less.
        """
        species_mean_fitness = \
            [species.mean_fitness for species in self.species]
        sum_mean_species_fitness = sum(species_mean_fitness)

        for species, mean_fitness in zip(self.species, species_mean_fitness):
            species.allotted_offspring_quota = \
                int(mean_fitness / sum_mean_species_fitness * self.n_pops)

    def not_so_natural_selection(self):
        """Perform selection on the population.

        Species champions (the fittest creature in a species) are carried over
        to the next generation (elitism). The worst performing proportion of
        each species is culled. R.I.P.
        """
        new_population = []

        for species in self.species:
            survivors = species.cull_the_weak(NeatAlgorithm.survival_threshold)
            new_population += survivors

        self.population = new_population

    def mating_season(self):
        """It is now time for mating season, time to make some babies.

        Replace the population with the next generation. Rip last generation.
        """
        ranked_species = sorted(self.species, key=lambda s: s.champion.fitness)
        worst_species = ranked_species[0]
        best_species = ranked_species[-1]
        the_champ = best_species.champion
        new_population = []

        total_expected_offspring = sum([species.allotted_offspring_quota
                                        for species in self.species])

        if total_expected_offspring < self.n_pops:
            pop_deficit = self.n_pops - total_expected_offspring

            best_species.allotted_offspring_quota += pop_deficit
            total_expected_offspring += pop_deficit
        elif total_expected_offspring > self.n_pops:
            pop_surplus = self.n_pops - total_expected_offspring
            worst_species.allotted_offspring_quota -= pop_surplus
            total_expected_offspring -= pop_surplus

        for species in self.species:
            new_population += species.next_generation(the_champ,
                                                      self.population)

        for species in filter(lambda s: s.is_extinct, self.species):
            print('\n' + '*' * 80)
            print("R.I.P. The species %s is kill after %d generations." %
                  (species, species.age))
            print('*' * 80 + '\n')
        self.species = set(filter(lambda s: not s.is_extinct, self.species))

        self.population = new_population
