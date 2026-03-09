
# 02_get_data_deprivation.py
# This script computes deprivation indices (empirical, euclidean, driving, and population-weighted) for H3 cells.
# Input: ../raw_data/GRDI_by_country/{Country}.csv, ../raw_data/OD/weekly/H37/od_week_h37_{country}_{year}.csv, ../data/population/population.json, ../raw_data/network/*.gml
# Output: ../data/tmp/*.csv

import pandas as pd
import networkx as nx
import numpy as np
import os
import h3
from datetime import datetime
from scipy.sparse import csr_matrix
from tqdm import tqdm
import json

# Configuration
RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "tmp")
NETWORK_DIR = os.path.join(RAW_DATA_DIR, "network")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

# 1. Load GRDI Data
path_grdi = os.path.join(RAW_DATA_DIR, 'GRDI_by_country/')
LIST_files = [ 'Mexico.csv', 'India.csv']
df_grdi = []
for f in LIST_files: 
    path = os.path.join(path_grdi, f)
    if not os.path.exists(path): continue
    df_f = pd.read_csv(path, index_col = 0)
    df_f['country'] = f.split('.csv')[0]
    df_grdi.append(df_f)

if not df_grdi:
    print("No GRDI data found.")
    exit()

df_grdi = pd.concat(df_grdi, axis=0)
if 'h3_7' not in df_grdi.columns:
    df_grdi['h3_7'] = df_grdi.apply( lambda x : h3.latlng_to_cell(x.lat, x.lon, 7), axis=1)

tmp_cells = df_grdi["h3_7"].tolist()

# 2. Part Empirical Data
COUNTRIES_EMPIRICAL = ["mx", "in"]
DICT_COUNTRY = {
    "mx":"mexico",
    "in":"india",
}

print("Processing Empirical Data...")
for countryID in tqdm(COUNTRIES_EMPIRICAL):
    countryname = DICT_COUNTRY[countryID]
    
    # Load OD 2019
    path_od_2019 = os.path.join(RAW_DATA_DIR, f"OD/weekly/H37/od_week_h37_{countryID}_2019.csv")
    if not os.path.exists(path_od_2019):
        print(f"Skipping {countryname}: OD 2019 not found.")
        continue
    od = pd.read_csv(path_od_2019)
    od["year"] = 2019
    od['date'] = pd.to_datetime(od['year'].astype(str) + od['week_number'].astype(str) + '1', format='%Y%W%w', errors='coerce') 

    # Load OD 2020
    path_od_2020 = os.path.join(RAW_DATA_DIR, f"OD/weekly/H37/od_week_h37_{countryID}_2020.csv")
    if os.path.exists(path_od_2020):
        od1 = pd.read_csv(path_od_2020)
        od1["year"] = 2020
        od1['date'] = pd.to_datetime(od1['year'].astype(str) + od1['week_number'].astype(str) + '1', format='%Y%W%w', errors='coerce')
        od = pd.concat([od, od1], axis=0)

    for case in ["pre-covid", "post-covid"]:
        df = pd.DataFrame()
        if case == "pre-covid":
            tmp_od = od[od["date"] < datetime(2020, 3, 1)]
        else:
            tmp_od = od[od["date"] > datetime(2020, 6, 15)]
        
        if tmp_od.empty: continue

        G = nx.DiGraph()
        g_od = tmp_od.groupby(by=["start_h3_7", "end_h3_7"])["trip_count"].sum().reset_index()
        g_od = g_od[g_od["start_h3_7"].isin(tmp_cells)]
        g_od = g_od[g_od["end_h3_7"].isin(tmp_cells)]
        g_od = g_od[g_od["start_h3_7"] != g_od["end_h3_7"]]
        
        for _, row in g_od.iterrows():
            u = row["start_h3_7"]
            v = row["end_h3_7"]
            G.add_edge(u, v, weight=row["trip_count"])
            
        nodes_to_remove = [node for node in G.nodes() if G.out_degree(node) < 3 and G.in_degree(node) < 3]
        G.remove_nodes_from(nodes_to_remove)
        
        if len(G) == 0: continue

        GN = nx.DiGraph()
        out_strength = {node: sum(data['weight'] for _, _, data in G.out_edges(node, data=True)) for node in G.nodes()}
        
        for u, v, data in G.edges(data=True):
            if out_strength[u] > 0:
                w = data['weight'] / out_strength[u]
                GN.add_edge(u, v, weight=w)
        
        nodes_order = list(GN.nodes())
        W = nx.to_numpy_array(GN, weight='weight', nodelist=nodes_order)
        
        tmp_grdi = df_grdi[df_grdi["h3_7"].isin(GN.nodes())].groupby(by=["h3_7"]).index_deprivation.mean().reset_index()
        dict_grdi = dict(zip(tmp_grdi['h3_7'], tmp_grdi['index_deprivation']))
        deprivation_indices = [dict_grdi.get(n, 0) for n in nodes_order]
        
        d_experienced = np.dot(W, deprivation_indices)
        df[case] = d_experienced
        df[case + "_cell"] = deprivation_indices
        df["cell"] = nodes_order
        
        out_path = os.path.join(OUTPUT_DIR, f"empirical_{case}_{countryname}.csv")
        df.to_csv(out_path, sep=",")

# 3. Euclidean Distance
def get_distance(threshold_time):
    velocity = 500  # 500 m/min = 30 km/h
    threshold_distance = threshold_time * velocity
    return threshold_distance

thresholds_minutes = [10, 15, 20, 30, 45, 60, 120]
thresholds_distances = [get_distance(t) for t in thresholds_minutes]

print("Processing Euclidean Data...")
for countryID in ["mx", "in"]:
    countryname = DICT_COUNTRY[countryID]
    gml_path = os.path.join(NETWORK_DIR, f"{countryname}_hexagons_euclidean.gml")
    
    if not os.path.exists(gml_path): continue
    
    graph_hexagon_mapped = nx.read_gml(gml_path)
    h3_mapped = df_grdi["h3_7"].tolist()
    nodes_to_remove = [node for node in graph_hexagon_mapped.nodes() if node not in h3_mapped]
    graph_hexagon_mapped.remove_nodes_from(nodes_to_remove)
    
    if len(graph_hexagon_mapped) == 0: continue

    tmp_grdi = df_grdi[df_grdi["h3_7"].isin(graph_hexagon_mapped.nodes())].groupby(by=["h3_7"]).index_deprivation.mean().reset_index()
    dict_grdi = dict(zip(tmp_grdi['h3_7'], tmp_grdi['index_deprivation']))
    nodes_order = list(graph_hexagon_mapped.nodes())
    deprivation_indices = [dict_grdi.get(n, 0) for n in nodes_order]
    
    W = nx.to_numpy_array(graph_hexagon_mapped, weight='weight', nodelist=nodes_order)
    df = pd.DataFrame()
    for d in thresholds_distances:
        filtered_matrix = np.where(W < d, W, 0)
        # Avoid division by zero
        filtered_matrix = np.where(filtered_matrix != 0, 1 / filtered_matrix, 0)
        row_sums = filtered_matrix.sum(axis=1, keepdims=True)
        normalized_matrix = np.divide(filtered_matrix, row_sums, where=row_sums!=0)
        d_experienced = np.dot(normalized_matrix, deprivation_indices)
        df[d] = d_experienced
        
    df["cell"] = nodes_order
    df.to_csv(os.path.join(OUTPUT_DIR, f"euclidean_{countryname}.csv"), sep=",")

# 4. Driving Travel Time
print("Processing Driving Data...")
for countryID in ["mx", "in"]:
    countryname = DICT_COUNTRY[countryID]
    gml_path = os.path.join(NETWORK_DIR, f"{countryname}_hexagons_driving.gml")
    
    if not os.path.exists(gml_path): continue
    
    graph_hexagon_mapped = nx.read_gml(gml_path)
    h3_mapped = df_grdi["h3_7"].tolist()
    nodes_to_remove = [node for node in graph_hexagon_mapped.nodes() if node not in h3_mapped]
    graph_hexagon_mapped.remove_nodes_from(nodes_to_remove)
    
    if len(graph_hexagon_mapped) == 0: continue

    tmp_grdi = df_grdi[df_grdi["h3_7"].isin(graph_hexagon_mapped.nodes())].groupby(by=["h3_7"]).index_deprivation.mean().reset_index()
    dict_grdi = dict(zip(tmp_grdi['h3_7'], tmp_grdi['index_deprivation']))
    nodes_order = list(graph_hexagon_mapped.nodes())
    deprivation_indices = [dict_grdi.get(n, 0) for n in nodes_order]
    
    W = nx.to_numpy_array(graph_hexagon_mapped, weight='weight', nodelist=nodes_order)
    df = pd.DataFrame()
    for d in thresholds_distances:
        filtered_matrix = np.where(W < d, W, 0)
        filtered_matrix = np.where(filtered_matrix != 0, 1 / filtered_matrix, 0)
        row_sums = filtered_matrix.sum(axis=1, keepdims=True)
        normalized_matrix = np.divide(filtered_matrix, row_sums, where=row_sums!=0)
        d_experienced = np.dot(normalized_matrix, deprivation_indices)
        df[d] = d_experienced
        
    df["cell"] = nodes_order
    df.to_csv(os.path.join(OUTPUT_DIR, f"driving_{countryname}.csv"), sep=",")

# 5. Population Weighted
print("Processing Population Weighted Data...")
pop_path = os.path.join(DATA_DIR, "population/population.json")
if not os.path.exists(pop_path):
    print("Population data missing, skipping population parts.")
else:
    with open(pop_path, "r") as inpuf:
        pop_dict = json.load(inpuf)
        
    # Recalculate Euclidean with Population
    for countryID in ["mx", "in"]:
        countryname = DICT_COUNTRY[countryID]
        gml_path = os.path.join(NETWORK_DIR, f"{countryname}_hexagons_euclidean.gml")
        if not os.path.exists(gml_path): continue
        
        graph_hexagon_mapped = nx.read_gml(gml_path)
        h3_mapped = df_grdi["h3_7"].tolist()
        nodes_to_remove = [node for node in graph_hexagon_mapped.nodes() if node not in h3_mapped]
        graph_hexagon_mapped.remove_nodes_from(nodes_to_remove)
        if len(graph_hexagon_mapped) == 0: continue

        tmp_grdi = df_grdi[df_grdi["h3_7"].isin(graph_hexagon_mapped.nodes())].groupby(by=["h3_7"]).index_deprivation.mean().reset_index()
        dict_grdi = dict(zip(tmp_grdi['h3_7'], tmp_grdi['index_deprivation']))
        nodes_order = list(graph_hexagon_mapped.nodes())
        deprivation_indices = [dict_grdi.get(n, 0) for n in nodes_order]
        
        P_ij = np.zeros((len(nodes_order), len(nodes_order)))
        for i, n_i in enumerate(nodes_order):
            for j, n_j in enumerate(nodes_order):
                P_ij[i][j] = pop_dict.get(n_i, 0) * pop_dict.get(n_j, 0)
        
        W = nx.to_numpy_array(graph_hexagon_mapped, weight='weight', nodelist=nodes_order)
        df = pd.DataFrame()
        for d in thresholds_distances:
            filtered_matrix = np.where(W < d, W, 0)
            filtered_matrix = np.where(filtered_matrix != 0, 1 / filtered_matrix, 0)
            filtered_matrix = filtered_matrix * P_ij # Population weighting
            row_sums = filtered_matrix.sum(axis=1, keepdims=True)
            normalized_matrix = np.divide(filtered_matrix, row_sums, where=row_sums!=0)
            d_experienced = np.dot(normalized_matrix, deprivation_indices)
            df[d] = d_experienced
            
        df["cell"] = nodes_order
        df.to_csv(os.path.join(OUTPUT_DIR, f"euclidean_population_{countryname}.csv"), sep=",")
        
    for countryID in ["mx","in"]:
        countryname = DICT_COUNTRY[countryID]
        gml_path = os.path.join(NETWORK_DIR, f"{countryname}_hexagons_driving.gml")
        if not os.path.exists(gml_path): continue
        
        graph_hexagon_mapped = nx.read_gml(gml_path)
        h3_mapped = df_grdi["h3_7"].tolist()
        nodes_to_remove = [node for node in graph_hexagon_mapped.nodes() if node not in h3_mapped]
        graph_hexagon_mapped.remove_nodes_from(nodes_to_remove)
        if len(graph_hexagon_mapped) == 0: continue

        tmp_grdi = df_grdi[df_grdi["h3_7"].isin(graph_hexagon_mapped.nodes())].groupby(by=["h3_7"]).index_deprivation.mean().reset_index()
        dict_grdi = dict(zip(tmp_grdi['h3_7'], tmp_grdi['index_deprivation']))
        nodes_order = list(graph_hexagon_mapped.nodes())
        deprivation_indices = [dict_grdi.get(n, 0) for n in nodes_order]
        
        P_ij = np.zeros((len(nodes_order), len(nodes_order)))
        for i, n_i in enumerate(nodes_order):
            for j, n_j in enumerate(nodes_order):
                P_ij[i][j] = pop_dict.get(n_i, 0) * pop_dict.get(n_j, 0)
        
        W = nx.to_numpy_array(graph_hexagon_mapped, weight='weight', nodelist=nodes_order)
        df = pd.DataFrame()
        for d in thresholds_distances:
            filtered_matrix = np.where(W < d, W, 0)
            filtered_matrix = np.where(filtered_matrix != 0, 1 / filtered_matrix, 0)
            filtered_matrix = filtered_matrix * P_ij 
            row_sums = filtered_matrix.sum(axis=1, keepdims=True)
            normalized_matrix = np.divide(filtered_matrix, row_sums, where=row_sums!=0)
            d_experienced = np.dot(normalized_matrix, deprivation_indices)
            df[d] = d_experienced
            
        df["cell"] = nodes_order
        df.to_csv(os.path.join(OUTPUT_DIR, f"driving_population_{countryname}.csv"), sep=",")

print("Done processing deprivation data.")
