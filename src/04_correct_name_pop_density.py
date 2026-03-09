
# 04_correct_name_pop_density.py
# This script corrects city names using external mappings and calculates population density for each city.
# Input: ../data/cities.geojson, ../data/population/population.json, ../raw_data/cities.yml, ../raw_data/mexico.geojson
# Output: ../data/cities/cities_info.geojson

import geopandas as gpd
import yaml
import json
import os
import pandas as pd

# Configuration
RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "cities")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

cities_path = os.path.join(DATA_DIR, "cities.geojson")
if not os.path.exists(cities_path):
    print("Cities data missing. Exiting.")
    exit()

gdf = gpd.read_file(cities_path)

cities_yml_path = os.path.join(RAW_DATA_DIR, "cities.yml")
#change mexico with india to do india
mexico_json_path = os.path.join(RAW_DATA_DIR, "mexico.geojson")

with open(cities_yml_path, 'r') as file:
    datayuan = yaml.safe_load(file)
    
with open(mexico_json_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

mx_data = {d["properties"]["name_city"]: d["properties"]["correct_name"] for d in geojson_data["features"]}
other_data = {k: v["name"] for (k, v) in datayuan.items()}

mapping = {}
for (k, v) in mx_data.items():
    mapping[k] = v
for (k, v) in other_data.items():
    mapping[k] = v

gdf["correct_name"] = gdf["name_city"].map(mapping)
gdf["correct_name"] = gdf["correct_name"].fillna(gdf["name_city"])


pop_path = os.path.join(DATA_DIR, "population/population.json")
with open(pop_path, 'r', encoding='utf-8') as f:
    population = json.load(f)

if "cell" in gdf.columns:
    gdf["population"] = gdf["cell"].map(population)
else:
    print("Warning: 'cell' column missing in cities.geojson")

if "correct_name" in gdf.columns and "population" in gdf.columns:
    result = gdf.dissolve(by=['correct_name', "name_city"], aggfunc={'population': 'sum'}).reset_index()    
    result = result.to_crs(epsg=6933)
    result['area_km2'] = result.geometry.area / 1e6
    result = result.to_crs(epsg=4326)
    
    result["pop_density"] = result["population"] / result["area_km2"]
    
    output_file = os.path.join(OUTPUT_DIR, "cities_info.geojson")
    result.to_file(output_file, driver="GeoJSON")
    print(f"Cities Info saved to {output_file}")
else:
    print("Error: Missing columns for aggregation.")
