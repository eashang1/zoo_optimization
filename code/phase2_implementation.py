#!/usr/bin/env python3

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
new_column_names = {
	"Cost/10 lb": "c1",
	"Welfare value": "w1",
	"Cost/10 lb.1": "c2",
	"Welfare value.1": "w2",
	"Cost/10 lb.2": "c3",
	"Welfare value.2": "w3"
}
species_data = species_data.rename(columns=new_column_names)

# join species data to animal data
animals = animals.merge(species_data, on="Species", how="left")

# add column for recommended food quantity by animal, remove extra columns
animals['adult_bool'] = (animals['Age'] >= animals['Adulthood Age']).astype(int)
animals['food_quantity'] = np.where(animals['adult_bool'] == 1, animals['Adult Recommended food'], animals['Child Recommended Food'])
animals = animals.drop(columns=['Age', 'Adulthood Age', 'Child Recommended Food', 'Adult Recommended food', 'adult_bool'])

# import facility investment sheet
attractions = pd.read_excel(file, sheet_name="Attractions", header=0)
attractions = attractions.rename(columns={"Estimated Monthly Attendance Increase/$10,000 Investment": "q"})
print(animals.to_string())
print(attractions.to_string())

# Create model
m = gp.Model("zoo")

# Create variables
food_types = [1, 2, 3]
x = m.addVars(animals.index, food_types, name="x")
a = m.addVars(attractions.index, name="a")

# Set objective
m.setObjective(sum([sum([x[i, j] * animals[f'w{j}'][i] for j in food_types]) / animals['food_quantity'][i] for i in animals.index]), GRB.MAXIMIZE)
obj = m.getObjective()
print(obj.getValue())

# Add constraints
m.addConstrs((a[k] <= 20000 for k in attractions.index), name="a_k")
m.addConstr(200000 + 0.003*np.dot(attractions["q"], [a[k] for k in attractions.index]) >= 1.05*(100000 + sum([a[k] for k in attractions.index]) + 9*sum([sum([x[i, j] * animals[f'c{j}'][i] for j in food_types]) for i in animals.index])), name="profit")
m.addConstrs((sum([x[i, j] for j in food_types]) == animals['food_quantity'][i] for i in animals.index), name="food")
m.addConstrs((a[k] >= 0 for k in attractions.index), name="sign1")
m.addConstrs((x[i, j] >= 0 for i in animals.index for j in food_types), name="sign2")

# Run
m.optimize()

# Results
for v in m.getVars():
	print(v.varName, v.x)
print('Obj: ', m.objVal)

