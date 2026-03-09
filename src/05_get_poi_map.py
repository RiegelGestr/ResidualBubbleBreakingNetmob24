
# 05_get_poi_map.py
# This script aggregates POI data into H3 cells within cities, calculating metrics like density, entropy, and Gini index.
# Input: ../data/cities/cities_info.geojson, ../data/cities.geojson, ../raw_data/pois/*
# Output: ../data/pois/pois_{country}_cell.csv

import geopandas as gpd
import pandas as pd
import numpy as np
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

RAW_DATA_DIR = "../raw_data"
DATA_DIR = "../data"
OUTPUT_DIR = os.path.join(DATA_DIR, "pois")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

ensure_dir(OUTPUT_DIR)

def enhanced_category_counts(series, all_categories):
    return series.value_counts().reindex(all_categories, fill_value=0).to_dict()

def adjusted_entropy(series, all_categories):
    counts = series.value_counts().reindex(all_categories, fill_value=0)
    proportions = counts / counts.sum()
    return -np.sum(proportions * np.log2(proportions + 1e-10))

def normalized_gini(series, all_categories):
    counts = series.value_counts().reindex(all_categories, fill_value=0)
    proportions = counts / counts.sum()
    return 1 - np.sum(proportions**2)

cities_info_path = os.path.join(DATA_DIR, "cities/cities_info.geojson")
cities_path = os.path.join(DATA_DIR, "cities.geojson")

if not os.path.exists(cities_info_path) or not os.path.exists(cities_path):
    print("City data missing. Exiting.")
    exit()

cities = gpd.read_file(cities_info_path)
dict_correct_name = {row["name_city"]: row["correct_name"] for _, row in cities.iterrows()}

gdf = gpd.read_file(cities_path)
gdf["correct_name"] = gdf["name_city"].map(dict_correct_name)
gdf["correct_name"] = gdf["correct_name"].fillna(gdf["name_city"])

countries = ["mexico", "india"]

for country in countries:
    print(f"Processing POIs for {country}...")
    pois_path = os.path.join(RAW_DATA_DIR, f"pois/pois_{country}.geoparquet")
    comm_path = os.path.join(RAW_DATA_DIR, f"pois/community_pois_{country}.csv")
    
    if not os.path.exists(pois_path) or not os.path.exists(comm_path):
        print(f"Skipping {country}: POI data missing.")
        continue
        
    pois_df = gpd.read_parquet(pois_path)
    pois_df = pois_df[pois_df["confidence"] > 0.9]
    
    categories = pd.read_csv(comm_path)
    categories.index = categories.node
    dict_cat = categories["name_community"].to_dict()
    
    pois_df["category"] = pois_df["categories"].apply(lambda x: x['primary'] if isinstance(x, dict) and 'primary' in x else None)
    pois_df["MetaCategory"] = pois_df["category"].map(dict_cat)
    pois_df["MetaCategory"] = pois_df["MetaCategory"].fillna("Other") # Fallback
    
    c_gdf = gdf[gdf["country"] == country]
    if c_gdf.empty: continue
    
    if pois_df.crs != c_gdf.crs:
        pois_df = pois_df.to_crs(c_gdf.crs)
        
    joined_data = gpd.sjoin(
        c_gdf,
        pois_df,
        how='left',
        predicate='contains'
    )
    
    all_categories = joined_data['MetaCategory'].unique().tolist()
    
    aggs = {
        'correct_name': 'first',
        'name_city': 'first',
        'geometry': 'first',
        'country': 'first',
        'MetaCategory': [
            ('total_count', 'count'),
            ('unique_count', 'nunique'),
            ('category_counts', lambda x: enhanced_category_counts(x, all_categories)),
            ('entropy', lambda x: adjusted_entropy(x, all_categories)),
            ('gini_index', lambda x: normalized_gini(x, all_categories))
        ]
    }
    
    result = joined_data.groupby('cell', as_index=False).agg(aggs)
    
    if isinstance(result.columns, pd.MultiIndex):
        new_cols = []
        for col in result.columns:
            if col[0] == 'MetaCategory':
                if col[1] == 'total_count': new_cols.append('Number of POI')
                elif col[1] == 'unique_count': new_cols.append('Number of Unique Categories')
                elif col[1] == 'category_counts': new_cols.append('Category Distribution in Cell')
                elif col[1] == 'entropy': new_cols.append('Entropy')
                elif col[1] == 'gini_index': new_cols.append('Gini')
            else:
                new_cols.append(col[0])
        result.columns = new_cols
    else:
        result.columns = ['cell', 'correct_name', 'name_city', 'geometry', 'country',
                        'Number of POI', 'Number of Unique Categories', 'Category Distribution in Cell',
                        'Entropy', 'Gini']

    output_file = os.path.join(OUTPUT_DIR, f"pois_{country}_cell.csv")
    result.to_csv(output_file, index=False)
    print(f"Saved {output_file}")
