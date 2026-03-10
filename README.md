
# Paper Title Residual Bubble Breaking

This folder contains a cleaned and structured workflow for ...

## Directory Structure
*   **`raw_data/`**: Contains raw input files (OD matrices, GRDI data, GADM, Street Networks, POIs). The data in this folder are dummy data, randomly generated to provide input for our analysis.
*   **`src/`**: Python scripts for data processing and generation.
*   **`data/`**: Directory where generated data will be saved. The subdirectories (`cities`, `pois`, `network`, `detour`, `tmp`, `population`)
## Execution Order
Run the scripts in `src/` in the following order to generate the full dataset:

1.  **`01_get_data_population.py`**:
    *   Generates `data/population/population.json` from raw population raster and GRDI.
2.  **`02_get_data_deprivation.py`**:
    *   Generates empirical, euclidean, and driving deprivation indices in `data/tmp/`.
3.  **`03_get_cities.py`**:
    *   Identifies city boundaries and generates `data/cities.geojson`.
4.  **`04_correct_name_pop_density.py`**:
    *   Refines city names and adds population density, saving to `data/cities/cities_info.geojson`.
5.  **`05_get_poi_map.py`**:
    *   Maps POIs to H3 cells and calculates diversity metrics. Output: `data/pois/pois_{country}_cell.csv`.
6.  **`06_get_detour_graph.py`**:
    *   Builds specific detour graphs from OD and street networks. Output: `data/network/{country}_detour.gml`.
7.  **`07_get_detour_metrics.py`**:
    *   Calculates detour metrics from the graphs. Output: `data/detour/{country}.csv`.
8.  **`08_get_network_gexf.py`**:
    *   Generates the final network files (`.gexf`) in `data/network/`.
9.  **`09_network_visualization.ipynb`**:
    *   Visualizes the mobility networks and deprivation levels (`.gexf` etc.) in `data/network/network_viz`. Output: Figures 1a-b.
10.  **`10_descriptive_analysis.ipynb`**:
    *   Performs descriptive analysis, statistical tests, and visualizations. Output: Figure 1d, Figure 2, Supplementary Figures 2-4.
11.  **`11_city_analysis.ipynb`**:
    *   Performs descriptive analysis on the cities and do visualizations of compact vs. sparse cities. Output: Supplementary Figures 3, 5.
12.  **`12_slx_modeling.ipynb`**:
    *   Performs SLX modeling and plot the results. Output: Figures 3, Figures 4a-c, Supplementary Figure 6.
13.  **`13_poi_density_diversity.ipynb`**:
    *   Performs regression analysis to explore POI entropy vs. density and plot the results. Output: Figure 4d.

## Requirements
*   Python 3.x
*   pandas, geopandas, networkx, numpy, scipy, h3, shapely, rasterio, tqdm, pyyaml, haversine, igraph (python-igraph)
