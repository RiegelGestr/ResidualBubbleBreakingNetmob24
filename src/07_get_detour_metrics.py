
# 07_get_detour_metrics.py
# This script calculates the average detour metric per H3 cell from the detour graph.
# Input: ../data/network/{country}_detour.gml
# Output: ../data/detour/{country}.csv

import networkx as nx
import pandas as pd
import os

RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "detour")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

countries = ["mexico", "india"]

for countryname in countries:
    print(f"Processing {countryname}...")
    gml_path = os.path.join(DATA_DIR, f"network/{countryname}_detour.gml")
    
    if not os.path.exists(gml_path):
        print(f"Skipping {countryname}: Detour graph missing.")
        continue
        
    G = nx.read_gml(gml_path)
    
    self_loops = list(nx.selfloop_edges(G))
    G.remove_edges_from(self_loops)
    
    normalized_strength = {}
    for node in G.nodes():
        edges = list(G.edges(node, data=True))
        degree = len(edges)
        
        if degree > 0:
            total_weight = sum(data.get('weight', 0) for _, _, data in edges)
            normalized_strength[node] = total_weight / degree
        else:
            normalized_strength[node] = 0
            
    df = pd.DataFrame()
    df["cell"] = list(normalized_strength.keys())
    df["detour"] = list(normalized_strength.values())
    
    output_file = os.path.join(OUTPUT_DIR, f"{countryname}.csv")
    df.to_csv(output_file, sep=",", index=False)
    print(f"Saved {output_file}")
