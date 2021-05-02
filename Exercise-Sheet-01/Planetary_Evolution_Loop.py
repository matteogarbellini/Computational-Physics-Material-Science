#!/usr/bin/env python3

"""
@author:    M. Garbellini
@email:     matteo.garbellini@studenti.unimi.it

Albert-Ludwigs-Universität Freiburg
Computational Physics: Material Science
Exercise Sheet 01 - Planetary Evolution

The following are the referenced equations in the code:
Eq (1) : Euler algorithm for r(t+dt) and v(t+dt)
Eq (2) : Verlet algorithm for r(t+dt) and v(t)
Eq (3) : Velocity-Verlet algorithm for r(t+dt) and v(t+dt)
Please see the report for an in depth formulation.

"""

import numpy as np
import sys
import itertools
import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

UNITS_OF_MASS = 1E29 #units of mass in kg
DT = 0.5 #simulation timestep
ITERATIONS = 2*365*500

AU = 1.49597870691E+11
AUday = 1.49597870691E+11/86400.
G_CONST = 6.67408E-11/(AUday**2)/AU


def load_planets():

    position = np.loadtxt("planets.txt", usecols=(0,1,2))
    velocity = np.loadtxt("planets.txt", usecols=(3,4,5))
    names = np.loadtxt("planets.txt", dtype=object, usecols=(6) )
    mass = np.loadtxt("mass.txt", usecols=(0))

    return names, mass, position, velocity

class Particle:

    def __init__(self,ID, name, mass, position, velocity):

        self.ID = ID
        self.name = name
        self.mass = mass

        # position and velocity arrays containing the informations
        # on current pos[0], previous pos[-1], next pos[1]
        self._position = np.stack((position, np.zeros(3), np.zeros(3)), axis=0)
        self._velocity = velocity

        # net force on particle
        self.net_force = np.zeros(3,dtype=np.float)
        self.v_verlet_net_force = np.zeros(3,dtype=np.float)

    def pos(self, timestamp):
        return self._position[timestamp,:]

    def vel(self):
        return self._velocity

    def set_vel(self, velocity):
        self._velocity = velocity

    def set_pos(self, position, timestamp):
        self._position[timestamp,:] = position

    def update_coord(self):
        self._position = np.stack((self.pos(1),np.zeros(3),self.pos(0)), axis=0)
        self.net_force = np.zeros(3,dtype=np.float)

    # Routine for printing on standard output the current coordinates
    # //the values are printed with precision to the 5th digit (by default)
    # //although can be overwritten by passing precision argument
    def print_current_coordinates(self, precision = 5):
        print(np.around(self.pos(0)[0], precision),np.around(self.pos(0)[1],precision), np.around(self.pos(0)[2],precision))


class System:

    def __init__(self, name):

        self.name = name
        self.planets = []
        self.time = 0

        # the energy values are instantaneous values
        # //history values are not saved on memory
        self.k_energy = None
        self.u_energy = None

    def add_planet(self,ID, name, mass, position, velocity):

        self.planets.append(Particle(ID,name, mass, position, velocity))

    # Routine for updating the planets coordinates. It is foundamental for optimal handling
    # of positions and velocities at different timestamp (t-dt, t, t+dt)
    # //the routine itself calls a routine implemented in the class particle
    # //the sun coordinates are not updated. It is assumed stationary (sun planet_ID = 0)
    def update_coordinates(self):
        for planet in self.planets:
            if(planet.ID > 0):
                planet.update_coord()


    # Routine for computing the force between two planets
    # //the function is called by compute_system_force which computes the force for all planets
    def compute_force(self, planet_1, planet_2, t_stamp):

        distance_cubed = (np.linalg.norm(planet_1.pos(t_stamp) - planet_2.pos(t_stamp)))**3
        force = G_CONST*planet_1.mass*planet_2.mass * np.reciprocal(distance_cubed) * (planet_1.pos(t_stamp) - planet_2.pos(t_stamp))
        planet_1.net_force += -force
        planet_2.net_force += +force

    # Routine for computing the force between all planets in the system
    # //t_stamp {-1,0,1} represents the position stored at t-dt, t and t+dt
    def compute_system_force(self, t_stamp):
        for planet_1, planet_2 in itertools.combinations(self.planets, 2):
            self.compute_force(planet_1, planet_2, t_stamp)

    # Routine for computing the kinetic energy of the system (evaluated at timestamp t)
    # //no need to store k_energy for each individual planet
    def compute_k_energy(self):

        # kinetic energy is set to zero each time it is required
        # to avoid unexpected values
        self.k_energy = 0
        for planet in self.planets:
            self.k_energy += 0.5*planet.mass*np.linalg.norm(planet.vel())


    # Routine for computing the potential energy of the system (evaluated at timestamp t)
    # //as for compute_system_force the routine is inefficient for large number of particles
    def compute_u_energy(self):

        # potential energy is set to zero each time it is required
        # to avoid unexpected values
        self.u_energy = 0
        for planet_1, planet_2 in itertools.combinations(self.planets, 2):
            distance = np.linalg.norm(planet_1.pos(0) - planet_2.pos(0))
            self.u_energy += -G_CONST*planet_1.mass*planet_2.mass * np.reciprocal(distance)


    # Routine for printing on standard output the current coordinates
    # //the values are printed with precision to the 5th digit (by default)
    # //although can be overwritten by passing precision argument
    def print_system_coordinates(self, precision = 5):
        for planet in self.planets:
            #coordinates.append(np.around(planet.pos(0)[0], precision))
            #coordinates.append(np.around(planet.pos(0)[1], precision))
            #coordinates.append(np.around(planet.pos(0)[2], precision))
            print(np.around(planet.pos(0)[0], precision), np.around(planet.pos(0)[1], precision), np.around(planet.pos(0)[2], precision), end=' ')
        print(np.around(self.k_energy,precision), np.around(self.u_energy,precision), np.around(self.k_energy+self.u_energy,precision))
        print("")

    # Routine that implements the Euler differential integrator
    # //the number of iterations is set globally
    # //the routine is essentially a double for loop -> slow for large number of particles
    # //a routine for saving computational results on an output file is called for each iteration
    def evolve_euler(self):
        iter = 0
        p_id = 0
        while iter < ITERATIONS:
            self.compute_k_energy()
            self.compute_u_energy()
            self.compute_system_force(0)
            for planet in self.planets:
                if(planet.ID != 0):
                    new_pos = planet.pos(0) + DT*planet.vel() + planet.net_force*DT*DT/planet.mass
                    new_vel = planet.vel() + DT*planet.net_force/planet.mass

                    planet.set_pos(new_pos, 1)
                    planet.set_vel(new_vel)

            iter += 1
            self.time += DT
            self.update_coordinates()
            self.print_system_coordinates()

    def evolve_verlet(self):
        iter = 0
        while iter<ITERATIONS:

            # If the current iteration is the first iteration it is necessary to
            # propagate the positions to the new "mid-positions", i.e shift the
            # initial conditions to first iteration
            if(iter == 0):
                self.compute_k_energy()
                self.compute_u_energy()
                self.compute_system_force(0)
                for planet in self.planets:
                    if(planet.name!="Sun"):
                        new_pos = planet.pos(0) + DT*planet.vel() + planet.net_force*DT*DT/planet.mass
                        planet.set_pos(new_pos, 1)

            else:
                self.compute_k_energy()
                self.compute_u_energy()
                self.compute_system_force(0)
                for planet in self.planets:
                    if(planet.ID != 0):
                        new_pos = 2*planet.pos(0) - planet.pos(-1) + planet.net_force*DT*DT/planet.mass
                        new_vel = (new_pos - planet.pos(-1))/(2*DT)

                        planet.set_pos(new_pos,1)
                        planet.set_vel(new_vel)

        iter += 1
        self.time += DT
        self.update_coordinates()
        self.print_system_coordinates()

    def evolve_velocity_verlet(self):
        iter = 0
        while iter < ITERATIONS:
            self.compute_k_energy()
            self.compute_u_energy()
            self.compute_system_force(0)
            for planet in self.planets:
                if(planet.ID != 0):
                    new_pos = planet.pos(0) + DT*planet.vel() + planet.net_force*DT*DT/planet.mass
                    planet.set_pos(new_pos,1)
                    planet.v_verlet_net_force = planet.net_force

            self.compute_system_force(1)
            for planet in self.planets:
                if(planet.ID != 0):
                    new_vel = planet.vel() + 0.5*DT*DT*(planet.net_force+planet.v_verlet_net_force)/planet.mass

            iter += 1
            self.time += DT
            self.update_coordinates()
            self.print_system_coordinates()



if __name__ == '__main__':

    planets_name, planets_mass, planets_pos, planets_vel = load_planets()

    SolarSystem = System("SolarSystem")
    for i in range(len(planets_name)):
        SolarSystem.add_planet(i,planets_name[i], planets_mass[i]*UNITS_OF_MASS, planets_pos[i], planets_vel[i])

    SolarSystem.evolve_euler()


    """
    with plt.style.context(['science', 'dark_background']):
        fig = plt.figure()
        ax = fig.add_subplot()
        for p in SolarSystem.planets:
            if(p.ID < 4):
                ax.plot(pos_x[p.ID,:], pos_y[p.ID,:], label=p.name)
        #ax.plot(pos_x[0,:], pos_y[0,:], label="Sun")
        #ax.legend(title='Order')
        #ax.set_xlim([-10E11,10E11])
        #ax.set_ylim([-10E11,10E11])
        #ax.autoscale(tight=True)
        fig.savefig('./Euler_Integrator.pdf')
    """
