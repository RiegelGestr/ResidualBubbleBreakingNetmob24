
# 06_get_detour_graph.py
# This script constructs a detour graph by analyzing street network detours compared to Euclidean distances for Origin-Destination flows.
# Input: ../raw_data/OD/weekly/H37/od_week_h37_*.csv, ../raw_data/preproc/osm_network_*.gml (or .graphml for India)
# Output: ../data/network/{country}_detour.gml

import pandas as pd
import networkx as nx
import geopandas as gpd
import numpy as np
import igraph as ig
from shapely.geometry import Polygon, Point
import h3
import random
from tqdm import tqdm
from haversine import haversine, Unit
import os

RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "network")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

def h3_to_polygon(h3_hex):
    # Hex string to polygon
    coords = h3.cell_to_boundary(h3_hex) # V4
    flipped = tuple((coord[1], coord[0]) for coord in coords)
    return Polygon(flipped)

def get_distance(threshold_time):
    velocity = 830
    threshold_distance = threshold_time * velocity
    return threshold_distance

def get_network_hexagons(countryID):
    dict_country = {
        "mx":"mexico",
        "in":"india",
    }
    
    if countryID not in dict_country:
        print(f"Skipping {countryID}: Not in dictionary.")
        return

    countryname = dict_country[countryID]
    print(f"Processing {countryname}...")
    
    path_2019 = os.path.join(RAW_DATA_DIR, f"OD/weekly/H37/od_week_h37_{countryID}_2019.csv")
    if not os.path.exists(path_2019):
         print(f"OD data 2019 missing for {countryname}")
         return
         
    od = pd.read_csv(path_2019)
    path_2020 = os.path.join(RAW_DATA_DIR, f"OD/weekly/H37/od_week_h37_{countryID}_2020.csv")
    if os.path.exists(path_2020):
        od1 = pd.read_csv(path_2020)
        od = pd.concat([od, od1], axis=0)

    hexagon_graph = nx.DiGraph()
    edges = set()
    for _,row in od.iterrows():
        u = row["start_h3_7"]
        v = row["end_h3_7"]
        if (u,v) in edges: continue
        hexagon_graph.add_edge(u,v)
        edges.add((u,v))

    mode_transport = "driving"
    name_graph = "osm_network_" + countryname + "_" + mode_transport
    
    if countryID == "in":
        graph_path = os.path.join(RAW_DATA_DIR, "preproc/india_filtered.graphml")
        if not os.path.exists(graph_path): return
        street_network = nx.read_graphml(graph_path)        
        tmp = []
        for node in street_network.nodes(data=True):
            if 'longitude' in node[1] and 'latitude' in node[1]:
                tmp.append({
                    "node": node[0],
                    "pos": Point(float(node[1]["longitude"]), float(node[1]["latitude"]))
                })
            elif 'x' in node[1] and 'y' in node[1]: # Fallback to x,y
                 tmp.append({
                    "node": node[0],
                    "pos": Point(float(node[1]["x"]), float(node[1]["y"]))
                })
    else:
        graph_path = os.path.join(RAW_DATA_DIR, f"preproc/{name_graph}.gml")
        if not os.path.exists(graph_path): 
             print(f"Network graph missing: {graph_path}")
             return
        street_network = nx.read_gml(graph_path)
        
        tmp = []
        for node in street_network.nodes(data=True):
             if 'x' in node[1] and 'y' in node[1]:
                tmp.append({
                    "node": node[0],
                    "pos": Point(float(node[1]["x"]), float(node[1]["y"]))
                })

    nodes_graph = pd.DataFrame(tmp)
    if nodes_graph.empty:
        print(f"No nodes found in street network for {countryname}")
        return

    nodes_graph = gpd.GeoDataFrame(nodes_graph, crs="EPSG:4326", geometry="pos")
    dict_pos_node = {row["node"]:row["pos"] for _,row in nodes_graph.iterrows()}

    hex_nodes = list(hexagon_graph.nodes())
    if not hex_nodes: return

    tmp_hex = [{"geometry": h3_to_polygon(n), "hexagon": n} for n in hex_nodes]
    df_hex = pd.DataFrame(tmp_hex)
    hexagons_gdf = gpd.GeoDataFrame(df_hex, crs="EPSG:4326", geometry="geometry")

    mapping = gpd.sjoin(nodes_graph, hexagons_gdf, how="left", predicate="within")
    mapping = mapping.dropna(subset=['hexagon'])
    
    dict_hexagon_to_intersections = mapping.groupby('hexagon')['node'].apply(list).to_dict()
    dict_intersection_to_hexagon = dict(zip(mapping['node'], mapping['hexagon']))

    nodes_to_remove = [node for node in hexagon_graph.nodes() if hexagon_graph.out_degree(node) < 3 and hexagon_graph.in_degree(node) < 3]
    hexagon_graph.remove_nodes_from(nodes_to_remove)

    hex_nodes = list(hexagon_graph.nodes())
    if not hex_nodes: return

    tmp_hex = [{"geometry": h3_to_polygon(n), "hexagon": n} for n in hex_nodes]
    df_hex = pd.DataFrame(tmp_hex)
    hexagons_starting_gdf = gpd.GeoDataFrame(df_hex, crs="EPSG:4326", geometry="geometry")
    hexagons_starting = hexagons_starting_gdf["hexagon"].tolist()

    hexagons_starting_gdf = hexagons_starting_gdf.to_crs("EPSG:3857")
    nodes_graph_proj = nodes_graph.to_crs("EPSG:3857")
    
    hexagons_starting_gdf['buffered'] = hexagons_starting_gdf.geometry.buffer(10_000)

    hexagon_points = {}
    buffer_gdf = hexagons_starting_gdf[['hexagon', 'buffered']].set_geometry('buffered')
    joined_points = gpd.sjoin(nodes_graph_proj, buffer_gdf, how='inner', predicate='within')
    
    hexagon_points = joined_points.groupby('hexagon')['node'].apply(list).to_dict()
    nx_nodes = list(street_network.nodes())
    nx_to_ig = {node: idx for idx, node in enumerate(nx_nodes)}
    ig_to_nx = {v: k for k, v in nx_to_ig.items()}
    
    edges_list = []
    weights_list = []
    for u, v, data in street_network.edges(data=True):
        if u in nx_to_ig and v in nx_to_ig:
            edges_list.append((nx_to_ig[u], nx_to_ig[v]))
            weights_list.append(data.get('weight', 0.0))

    h = ig.Graph(len(nx_nodes), edges=edges_list, directed=True)
    h.es['weight'] = weights_list

    hexagon_points_ig = {k: [nx_to_ig[v] for v in vs if v in nx_to_ig] for (k, vs) in hexagon_points.items()}

    threshold_distance = get_distance(120)
    Number_sampling = 10

    graph_hexagon_mapped = nx.DiGraph()

    for hexagon_source in tqdm(hexagons_starting):
        if hexagon_source not in hexagon_points_ig: continue
        
        nodes_filter_ig = hexagon_points_ig[hexagon_source]
        if not nodes_filter_ig: continue

        
        subgraph_h = h.subgraph(nodes_filter_ig)
        
        # Sampling intersections
        if hexagon_source not in dict_hexagon_to_intersections: continue
        intersections = dict_hexagon_to_intersections[hexagon_source]
        
        valid_intersections = [i for i in intersections if i in nx_to_ig]
        if not valid_intersections: continue
        
        samples = [random.choice(valid_intersections) for _ in range(Number_sampling)]
        dict_sampling = {i: samples.count(i) for i in set(samples)}
        
        ig_to_sub = {ig_idx: sub_idx for sub_idx, ig_idx in enumerate(nodes_filter_ig)}
        
        nodes_id_sub = []
        nodes_id_original_nx = []
        counts = []
        
        for nx_node, count in dict_sampling.items():
            ig_node = nx_to_ig[nx_node]
            if ig_node in ig_to_sub:
                nodes_id_sub.append(ig_to_sub[ig_node])
                nodes_id_original_nx.append(nx_node)
                counts.append(count)
        
        if not nodes_id_sub: continue

        dists = subgraph_h.distances(source=nodes_id_sub, weights="weight", mode="out")
        dists = np.array(dists) 
        
        tmp_hexagon_reached = {}
        tmp_hexagon_detour = {}
        
        for src_idx, src_sub_id in enumerate(nodes_id_sub):
            d_array = dists[src_idx]
            count = counts[src_idx]
            src_nx = nodes_id_original_nx[src_idx]
            
            valid_indices = np.where(d_array <= threshold_distance)[0]
            
            for dest_sub_id in valid_indices:
                dist = d_array[dest_sub_id]
                
                if dest_sub_id >= len(nodes_filter_ig): continue # Should not happen
                dest_ig = nodes_filter_ig[dest_sub_id]
                dest_nx = ig_to_nx[dest_ig]
                
                if dest_nx not in dict_intersection_to_hexagon: continue
                
                hex_reached = dict_intersection_to_hexagon[dest_nx]
                
                p0 = dict_pos_node[src_nx]
                p1 = dict_pos_node[dest_nx]
                pos_A = (p0.y, p0.x)
                pos_B = (p1.y, p1.x)
                euclidean = haversine(pos_A, pos_B, unit=Unit.METERS)
                
                if euclidean == 0: continue
                
                detour = dist / euclidean
                
                if hex_reached not in tmp_hexagon_reached:
                     tmp_hexagon_reached[hex_reached] = []
                     tmp_hexagon_detour[hex_reached] = []
                
                tmp_hexagon_reached[hex_reached].extend([dist] * count)
                tmp_hexagon_detour[hex_reached].extend([detour] * count)

        for hex_reached, ds in tmp_hexagon_reached.items():
            avg_dist = np.mean(ds)
            if avg_dist > threshold_distance: continue
            
            avg_detour = np.nanmean(tmp_hexagon_detour[hex_reached])
            if np.isnan(avg_detour): continue
            
            graph_hexagon_mapped.add_edge(hexagon_source, hex_reached, weight=float(avg_detour))

    out_path = os.path.join(OUTPUT_DIR, f"{countryname}_detour.gml")
    nx.write_gml(graph_hexagon_mapped, out_path)
    print(f"Saved {out_path}")

for code in ["mx", "id"]:
    get_network_hexagons(code)
