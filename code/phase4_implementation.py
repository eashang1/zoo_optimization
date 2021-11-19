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

new_column_names1 = {
    "Adult Recommended food": "g",
    "Cost/10 lb": "e1",
    "Welfare value": "f1",
    "Cost/10 lb.1": "e2",
    "Welfare value.1": "f2",
    "Cost/10 lb.2": "e3",
    "Welfare value.2": "f3"
}

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

# create dictionary which gives the welfare score for a certain food type for a species


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
m.addConstrs((a[k] <= 20000 for k in attractions.index), name="a_k")
m.addConstr(200000 + 0.003 * np.dot(attractions["q"], [a[k] for k in attractions.index]) >= 1.05 * (
        100000 + gp.quicksum([a[k] for k in attractions.index]) + 9 * gp.quicksum(
    [gp.quicksum([x[i, j] * animals[f'c{j}'][i] for j in food_types]) for i in animals.index]) +
        9 * (gp.quicksum([gp.quicksum(
    [gurobipy.quicksum([(d[n, j, m] * species[f'e{j}'][m]) for m in species_series.index]) for j in food_types]) for n
                          in adoption]))), name="profit")
m.addConstrs((gp.quicksum([x[i, j] for j in food_types]) == animals['food_quantity'][i] for i in animals.index),
             name="food")

m.addConstrs(((z[m] >= y[m]) for m in species.index), name="binary y1")
m.addConstrs(((z[m] <= 1000*y[m]) for m in species.index), name="binary y2")

m.addConstrs(((z[m]-n >= -1000*(1-h[n, m])) for n in adoption for m in species.index), name="binary h1")
m.addConstrs(((z[m]-n <= 1000*h[n, m]) for n in adoption for m in species.index), name="binary h2")

m.addConstrs(((gp.quicksum([d[n, j, m] for j in food_types]) == h[n, m] * species['g'][m]) for n in adoption for m in
              species.index), name="adopted food")

m.addConstr(gp.quicksum([z[m] for m in species.index]) >= 5, name="minimum adopted animals")

big_cats = [5, 6, 7, 10]
m.addConstrs((z[m - 1] <= 4 for m in big_cats), name="maximum adopted big cats")

not_big_cats = [1, 2, 3, 4, 8, 9, 11, 12, 13, 14]
m.addConstrs((z[m - 1] <= 4 for m in not_big_cats), name="maximum adopted not big cats")

m.addConstr(gp.quicksum([y[m] for m in big_cats]) <= 1, name="adopt at most one big cat")

new_species = [1, 4, 12, 13, 14]
m.addConstr(gp.quicksum([y[m - 1] for m in new_species]) <= 1, name="at most one new species")

existing_species = [2, 3, 8, 9, 11]
m.addConstr(gp.quicksum([y[m - 1] for m in existing_species]) <= 2, name="at most two existing species")

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
