
# 03_get_cities.py
# This script identifies city boundaries by clustering connected components of H3 cells based on mobility data,
# and then names them using GADM administrative areas.
# Input: ../data/tmp/empirical_pre-covid_{country}.csv, ../data/tmp/driving_{country}.csv, ../raw_data/gadm_410.gpkg
# Output: ../data/cities.geojson

import pandas as pd
import networkx as nx
import numpy as np
import geopandas as gpd
from tqdm import tqdm
import h3
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from libpysal import weights
import os

# Configuration
RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = DATA_DIR

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

def h3_to_polygon(h3_hex):
    # Hex string to polygon
    coords = h3.cell_to_boundary(h3_hex)
    flipped = tuple((coord[1], coord[0]) for coord in coords)
    return Polygon(flipped)

# 1. Load GADM
gadm_path = os.path.join(RAW_DATA_DIR, "gadm_410.gpkg")
if not os.path.exists(gadm_path):
    print("GADM data not found, cannot name cities. Exiting.")
    exit()

gadm = gpd.read_file(gadm_path)

dict_country = {
    "mx":"mexico",
    "in":"india",
}
threshold = 25 # Minimum cluster size

outpuf = []
print("Clustering Cities...")
for countryID, countryname in dict_country.items():
    # Pre Covid
    path_pre = os.path.join(DATA_DIR, f"tmp/empirical_pre-covid_{countryname}.csv")
    path_driving = os.path.join(DATA_DIR, f"tmp/driving_{countryname}.csv")
    
    if not os.path.exists(path_pre) or not os.path.exists(path_driving):
        print(f"Skipping {countryname}: Input data missing in tmp/")
        continue
        
    df_pre_covid = pd.read_csv(path_pre)
    df_pre_covid["geom"] = df_pre_covid["cell"].apply(h3_to_polygon)
    df_pre_covid = gpd.GeoDataFrame(df_pre_covid, geometry="geom", crs="EPSG:4326")
    
    # Driving / Theoretical
    df_driving = pd.read_csv(path_driving)
    
    # Merge
    df = pd.merge(df_pre_covid, df_driving, on="cell", how="inner")
    
    try:
        w = weights.Queen.from_dataframe(df, use_index=True, silence_warnings=True)
        G = w.to_networkx()
    except Exception as e:
        print(f"Warning: Could not build weights for {countryname} ({e}). Skipping.")
        continue

    id_mapping = df["cell"].to_dict()
    mapping = {i: row['cell'] for i, row in df.iterrows()}
    G = nx.relabel_nodes(G, mapping)
    
    cell_geom = {row["cell"]: row["geom"] for _, row in df.iterrows()}
    
    id_comp = 0
    for comp in nx.connected_components(G):
        if len(comp) >= threshold:
            for node in comp:
                outpuf.append({
                    "cell": node,
                    "component": id_comp,
                    "country": countryname,
                    "key": countryname + str(id_comp),
                    "geom": cell_geom[node]
                })
            id_comp += 1

if not outpuf:
    print("No cities found (threshold might be too high for dummy data).")
    # Proceeding with empty or exiting? Standard script output implies something.
    # I'll output an empty GeoDataFrame structure if needed but exit is safer.
    pass

ldf = pd.DataFrame(outpuf)
if ldf.empty:
    print("No cities dataframe created.")
    exit()

gdf = gpd.GeoDataFrame(ldf, geometry="geom", crs="EPSG:4326")

print("Naming Cities...")
if 'NAME_2' in gadm.columns:
    name_2_gadm = gadm.groupby('NAME_2').agg({
        'geometry': lambda x: unary_union(x)
    }).reset_index()
    name_2_gadm = gpd.GeoDataFrame(name_2_gadm, geometry='geometry', crs=gadm.crs)
else:
    name_2_gadm = gadm

comp_gdf = gdf.groupby(['key']).agg({
    'geom': lambda x: unary_union(x)
}).reset_index()
comp_gdf = gpd.GeoDataFrame(comp_gdf, geometry='geom', crs=gdf.crs)

mapping_results = []
for idx2, row2 in tqdm(comp_gdf.iterrows(), total=comp_gdf.shape[0]):
    max_overlap = 0
    best_match = None    
    for idx1, row1 in name_2_gadm.iterrows():
        if not row2.geom.intersects(row1.geometry): continue
        intersection = row2.geom.intersection(row1.geometry)
        overlap_area = intersection.area
        if overlap_area > max_overlap:
            max_overlap = overlap_area
            best_match = row1["NAME_2"]
            
    mapping_results.append({
        'gdf2_index': row2["key"],
        'matched_gdf1_index': best_match
    })

mr = {r["gdf2_index"]: r["matched_gdf1_index"] for r in mapping_results}
gdf["name_city"] = gdf["key"].map(mr)
if "key" in gdf.columns:
    del gdf["key"]

output_file = os.path.join(OUTPUT_DIR, "cities.geojson")
gdf.to_file(output_file, driver='GeoJSON')
print(f"Cities data saved to {output_file}")
