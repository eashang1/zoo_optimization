#!/usr/bin/env python3
import gurobipy
import pandas as pd
import numpy as np
import os.path
import gurobipy as gp
from gurobipy import GRB

# specify file name in local file structure
file = os.path.dirname(__file__) + "/../data/raw/zoo data.xlsx"

# import animals sheet
animals = pd.read_excel(file, sheet_name="Animals", usecols="A:C")

# aligning the species mismatch between the animals and species data tables
animals['Species'] = animals['Species'].replace(['Leopard'], 'Clouded Leopard')
animals['Species'] = animals['Species'].replace(['Alligator'], 'American Alligator')

# import and modify column titles for species data sheet
species_data = pd.read_excel(file, sheet_name="Species Data", header=1)
species = species_data.copy()

# column names for species data
new_column_names1 = {
    "Adult Recommended food": "g",
    "Cost/10 lb": "e1",
    "Welfare value": "f1",
    "Cost/10 lb.1": "e2",
    "Welfare value.1": "f2",
    "Cost/10 lb.2": "e3",
    "Welfare value.2": "f3"
}

# column names for animal data
new_column_names = {
    "Cost/10 lb": "c1",
    "Welfare value": "w1",
    "Cost/10 lb.1": "c2",
    "Welfare value.1": "w2",
    "Cost/10 lb.2": "c3",
    "Welfare value.2": "w3"
}
species_data = species_data.rename(columns=new_column_names)

# species_data1 is Species Data on excel with columns named for new variables (e,f,g)
species = species.rename(columns=new_column_names1)
print(species)

# join species data to animal data
animals = animals.merge(species_data, on="Species", how="left")

# create series of species
species_series = species["Species"]

# add column for recommended food quantity by animal, remove extra columns
animals['adult_bool'] = (animals['Age'] >= animals['Adulthood Age']).astype(int)
animals['food_quantity'] = np.where(animals['adult_bool'] == 1, animals['Adult Recommended food'],
                                    animals['Child Recommended Food'])
animals = animals.drop(
    columns=['Age', 'Adulthood Age', 'Child Recommended Food', 'Adult Recommended food', 'adult_bool'])

# import facility investment sheet
attractions = pd.read_excel(file, sheet_name="Attractions", header=0)
attractions = attractions.rename(columns={"Estimated Monthly Attendance Increase/$10,000 Investment": "q"})
print(animals.to_string())

# Create model
m = gp.Model("zooMIP")

# Create variables
# x_ij = amount of food for animal i of type
# a_k = amount invested in facility k
# z_m = number of animals of species m adopted
# d_njm = amount of food of type j for nth animal of species m
# y_m = 1 if species of type m was adopted, 0 otherwise
# h_nm = 1 if nth animal of species m  was adopted, 0 otherwise
food_types = [1, 2, 3]
adoption = [1, 2, 3, 4, 5]
x = m.addVars(animals.index, food_types, name="x")
a = m.addVars(attractions.index, name="a")
z = m.addVars(species_series.index, name="z")
d = m.addVars(adoption, food_types, species.index, name="d")
y = m.addVars(species_series.index, vtype=GRB.BINARY, name="y")
h = m.addVars(adoption, species_series.index, vtype=GRB.BINARY, name="h")

# Set objective
m.setObjective(gp.quicksum(
    [gp.quicksum([x[i, j] * animals[f'w{j}'][i] for j in food_types]) / animals['food_quantity'][i] for i in
     animals.index]) +
               (gp.quicksum([
                   gp.quicksum([
                       gurobipy.quicksum(
                           [(d[n, j, m] * species[f'f{j}'][m] / species['g'][m]) for m in species_series.index]) for j
                       in food_types]) for n in adoption])
               ), GRB.MAXIMIZE)
obj = m.getObjective()
print(obj.getValue())

# Add constraints

# Maximum spending limit on each attraction
m.addConstrs((a[k] <= 20000 for k in attractions.index), name="a_k")

# Cost/revenue constraint
m.addConstr(200000 + 0.003 * np.dot(attractions["q"], [a[k] for k in attractions.index]) >= 1.05 * (
        100000 + gp.quicksum([a[k] for k in attractions.index]) + 9 * gp.quicksum(
    [gp.quicksum([x[i, j] * animals[f'c{j}'][i] for j in food_types]) for i in animals.index]) +
        9 * (gp.quicksum([gp.quicksum(
    [gurobipy.quicksum([(d[n, j, m] * species[f'e{j}'][m]) for m in species_series.index]) for j in food_types]) for n
                          in adoption]))), name="profit")

# Food constraint for original animals
m.addConstrs((gp.quicksum([x[i, j] for j in food_types]) == animals['food_quantity'][i] for i in animals.index),
             name="food")

# y_m = 1 if species of type m was adopted, 0 otherwise
m.addConstrs(((z[m] >= y[m]) for m in species.index), name="binary y1")
m.addConstrs(((z[m] <= 1000*y[m]) for m in species.index), name="binary y2")

# h_nm = 1 if nth animal of species m  was adopted, 0 otherwise
m.addConstrs(((z[m]-n >= -1000*(1-h[n, m])) for n in adoption for m in species.index), name="binary h1")
m.addConstrs(((z[m]-n <= 1000*h[n, m]) for n in adoption for m in species.index), name="binary h2")

# Food constraint for adopted animals
m.addConstrs(((gp.quicksum([d[n, j, m] for j in food_types]) == h[n, m] * species['g'][m]) for n in adoption for m in
              species.index), name="adopted food")

# Must adopt at least five animals
m.addConstr(gp.quicksum([z[m] for m in species.index]) >= 5, name="minimum adopted animals")

# Can adopt at most four for big cat species (since can adopt species that changed enclosures)
big_cats = [5, 6, 7, 10]
m.addConstrs((z[m - 1] <= 4 for m in big_cats), name="maximum adopted big cats")

# Can adopt at most two individuals of any non-cat species
not_big_cats = [1, 2, 3, 4, 8, 9, 11, 12, 13, 14]
m.addConstrs((z[m - 1] <= 2 for m in not_big_cats), name="maximum adopted not big cats")

# Can adopt at most one species of big cat
m.addConstr(gp.quicksum([y[m] for m in big_cats]) <= 1, name="adopt at most one big cat")

# Can adopt at most one new species
new_species = [1, 4, 12, 13, 14]
m.addConstr(gp.quicksum([y[m - 1] for m in new_species]) <= 1, name="at most one new species")

# Can modify at most two existing enclosures
existing_species = [2, 3, 8, 9, 11]
m.addConstr(gp.quicksum([y[m - 1] for m in existing_species]) <= 2, name="at most two existing species")

# Nonnegativity constraints
m.addConstrs((a[k] >= 0 for k in attractions.index), name="sign a")
m.addConstrs((x[i, j] >= 0 for i in animals.index for j in food_types), name="sign x")
m.addConstrs((z[m] >= 0 for m in species.index), name="sign z")
m.addConstrs((d[n, j, m] >= 0 for n in adoption for j in food_types for m in species.index), name="sign d")

# Run
m.optimize()

# Results
for v in m.getVars():
    print(v.varName, v.x)
print('Obj: ', m.objVal)
