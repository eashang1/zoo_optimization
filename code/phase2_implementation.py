#!/usr/bin/env python3

import pandas as pd
import numpy as np
import os.path


def import_data():
	# specify file name in local file structure
	file = os.path.dirname(__file__) + "/../data/raw/zoo data.xlsx"

	# import animals sheet
	animals = pd.read_excel(file, sheet_name="Animals", usecols="A:C")

	# aligning the species mismatch between the animals and species data tables
	# TODO let's talk through how we feel about this vs. renaming in file
	animals['Species'] = animals['Species'].replace(['Leopard'], 'Clouded Leopard')
	animals['Species'] = animals['Species'].replace(['Alligator'], 'American Alligator')

	# import and modify column titles for species data sheet
	species_data = pd.read_excel(file, sheet_name="Species Data", header=1)
	new_column_names = {
		"Cost/10 lb": "food1_10lb_cost",
		"Welfare value": "food1_welfare",
		"Cost/10 lb.1": "food2_10lb_cost",
		"Welfare value.1": "food2_welfare",
		"Cost/10 lb.2": "food3_10lb_cost",
		"Welfare value.2": "food3_welfare"
	}
	species_data = species_data.rename(columns=new_column_names)

	# join species data to animal data
	animals = animals.merge(species_data, on="Species", how="left")

	# add column for recommended food quantity by animal, remove extra columns
	animals['adult_bool'] = (animals['Age'] >= animals['Adulthood Age']).astype(int)
	animals['food_quantity'] = np.where(animals['adult_bool'] == 1, animals['Adult Recommended food'], animals['Child Recommended Food'])
	animals = animals.drop(columns=['Age', 'Adulthood Age', 'Child Recommended Food', 'Adult Recommended food', 'adult_bool'])
	print(animals.to_string())

	# import facility investment sheet
	attractions = pd.read_excel(file, sheet_name="Attractions", header=0)

	return animals, attractions
