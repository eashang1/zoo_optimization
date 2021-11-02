#!/usr/bin/env python3

import pandas as pd
import os.path


def import_data():
	# specify file name in local file structure
	file = os.path.dirname(__file__) + "/../data/raw/zoo data.xlsx"

	# import animals sheet
	animals = pd.read_excel(file, sheet_name="Animals", usecols="A:C")

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

	# import facility investment sheet
	attractions = pd.read_excel(file, sheet_name="Attractions", header=0)

	return animals, species_data, attractions


