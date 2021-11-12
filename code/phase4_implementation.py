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
