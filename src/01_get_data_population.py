
# 01_get_data_population.py
# This script processes the raw population raster and GRDI data to create a population JSON file mapped to H3 cells.
# Input: ../raw_data/GRDI_by_country/{Country}.csv, ../raw_data/population/world_pop_1km.tif
# Output: ../data/population/population.json

import geopandas as gpd
import h3
import json
import rasterio
import pandas as pd
import os
from shapely.geometry import Point
from tqdm import tqdm

# Configuration
RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "population")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

# 1. Load GRDI Data
path_grdi = os.path.join(RAW_DATA_DIR, 'GRDI_by_country/')
LIST_files = ['Mexico.csv', 'India.csv']

df_grdi = []
for f in LIST_files: 
    file_path = os.path.join(path_grdi, f)
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found. Skipping.")
        continue
    df_f = pd.read_csv(file_path, index_col=0)
    df_f['country'] = f.split('.csv')[0]
    df_grdi.append(df_f)

if not df_grdi:
    print("No GRDI data found.")
    exit()

df_grdi = pd.concat(df_grdi, axis=0)
# Ensure h3_7 exists
if 'h3_7' not in df_grdi.columns:
    # h3 v4 API: latlng_to_cell
    df_grdi['h3_7'] = df_grdi.apply(lambda x: h3.latlng_to_cell(x.lat, x.lon, 7), axis=1)

df_grdi['geometry'] = df_grdi.apply(lambda x: Point(x.lon, x.lat), axis=1)
gdf_h = gpd.GeoDataFrame(df_grdi, geometry='geometry', crs="EPSG:4326")

# 2. Sample Raster Data
raster_path = os.path.join(RAW_DATA_DIR, 'population/world_pop_1km.tif')
if not os.path.exists(raster_path):
    print(f"Error: {raster_path} not found.")
    exit()

with rasterio.open(raster_path) as raster:
    if gdf_h.crs != raster.crs:
         gdf_h = gdf_h.to_crs(raster.crs)
    
    # Sample the raster
    coords = [(x,y) for x, y in zip(gdf_h.geometry.x, gdf_h.geometry.y)]
    sampled = raster.sample(coords)
    gdf_h['grdi'] = [x[0] for x in sampled]

gdf_h.loc[gdf_h['grdi'] < 0, 'grdi'] = 0
hex_df = gdf_h.groupby(by=["h3_7"])["grdi"].mean().reset_index()

hex_df["grdi"] /= 5

dict_pop = hex_df.set_index('h3_7')['grdi'].to_dict()

output_file = os.path.join(OUTPUT_DIR, "population.json")
with open(output_file, "w") as outpuf:
    json.dump(dict_pop, outpuf)

print(f"Population data saved to {output_file}")
