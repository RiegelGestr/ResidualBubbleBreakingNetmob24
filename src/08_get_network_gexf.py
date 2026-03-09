
# 08_get_network_gexf.py
# This script generates Gephi network files (.gexf) visualizing mobility flows between H3 cells,
# colored by deprivation index.
# Input: ../raw_data/GRDI_by_country/*.csv, ../raw_data/OD/weekly/H37/od_week_h37_*.csv, ../data/cities.geojson
# Output: ../data/network/{country}.gexf

import pandas as pd
import numpy as np 
import networkx as nx
import os
import h3
import geopandas as gpd

RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "network")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

path_grdi = os.path.join(RAW_DATA_DIR, "GRDI_by_country/")
list_files = ['Mexico.csv', 'India.csv']
df_grdi = []

for f in list_files:
    file_path = os.path.join(path_grdi, f)
    if not os.path.exists(file_path): continue
    df_f = pd.read_csv(file_path, index_col=0)
    df_f['country'] = f.split('.csv')[0]
    df_grdi.append(df_f)

if not df_grdi:
    print("No GRDI data found. Exiting.")
    exit()

df_grdi = pd.concat(df_grdi, axis=0)
if 'h3_7' not in df_grdi.columns:
    df_grdi['h3_7'] = df_grdi.apply( lambda x : h3.latlng_to_cell(x.lat, x.lon, 7), axis=1)

df_grdi.index = df_grdi["h3_7"]
dict_depriv = df_grdi["index_deprivation"].to_dict()

cities_path = os.path.join(DATA_DIR, "cities.geojson")
if not os.path.exists(cities_path):
    print("Cities GeoJSON missing. Exiting.")
    exit()

cities = gpd.read_file(cities_path)

cities["centroid"] = cities.geometry.centroid
cities['longitude'] = cities['centroid'].x
cities['latitude'] = cities['centroid'].y

cells_to_keep = cities["cell"].tolist()
dict_pos = {row["cell"]: (row["longitude"], row["latitude"]) for _, row in cities.iterrows()}

dict_country = {
    "mx": "mexico",
    "in": "india",
}

for countryID, country_name in dict_country.items():
    print(f"Processing Network for {country_name}...")
    G = nx.DiGraph()
    
    for year in ["2019", "2020"]:
        input_string = os.path.join(RAW_DATA_DIR, f"OD/weekly/H37/od_week_h37_{countryID}_{year}.csv")
        if not os.path.exists(input_string): continue
        
        od = pd.read_csv(input_string)
        weeks = od["week_number"].unique()
        
        for week in weeks:
            od_week = od[od["week_number"] == week]
            od_week = od_week[od_week["start_h3_7"] != od_week["end_h3_7"]]
            
            od_week = od_week[od_week["start_h3_7"].isin(cells_to_keep)]
            od_week = od_week[od_week["end_h3_7"].isin(cells_to_keep)]
            
            grouped = od_week.groupby(["start_h3_7", "end_h3_7"])["trip_count"].sum().reset_index()
            
            for _, row in grouped.iterrows():
                u, v, w = row["start_h3_7"], row["end_h3_7"], row["trip_count"]
                if G.has_edge(u, v):
                    G.edges[u, v]["weight"] += w
                else:
                    G.add_edge(u, v, weight=w)
                    
    for n in list(G.nodes()): # List copy to avoid modification issues if removing
        if n not in dict_depriv:
            pass
        else:
            G.nodes[n]["deprivation"] = dict_depriv[n]
            
        if n in dict_pos:
            G.nodes[n]["longitude"] = dict_pos[n][0] # viz:position x
            G.nodes[n]["latitude"] = dict_pos[n][1] # viz:position y
            
    self_loops = list(nx.selfloop_edges(G))
    G.remove_edges_from(self_loops)
    
    output_file = os.path.join(OUTPUT_DIR, f"{country_name}.gexf")
    nx.write_gexf(G, output_file)
    print(f"Saved {output_file}")
