
# Urban mobility enables deprivation bubble breaking in Indian and Mexican cities

This repository contains data and code to reproduce the analysis presented in the paper "Urban mobility enables deprivation bubble breaking in Indian and Mexican cities" by Yuan Liao, Federico Delussu, Sílvia de Sojo, Laura Alessandretti, and Antonio Desiderio.

## Abstract
Urban deprivation is traditionally measured using static, residence-based indicators, capturing the socioeconomic, demographic, and spatial conditions of neighborhoods.
However, this approach overlooks how daily movement allows residents to navigate the city, potentially exposing them to opportunities that differ significantly from their residential environments.
To bridge this gap, we quantify the extent of bubble breaking -- travel to less deprived areas -- by analyzing mobile phone mobility networks combined with satellite-derived deprivation indices across 64 cities in India and Mexico.
We find that residents of deprived areas systematically travel to better-off locations to meet daily needs, exhibiting a compensatory mobility pattern that significantly exceeds expectations derived from gravity models based on population and road networks.
This residual bubble breaking (the part gravity models can not explain) is associated with a tension in the built environment: while high local amenity diversity allows residents to satisfy needs locally, high amenity density and positive spillovers from neighboring areas is associated with movement across socioeconomic boundaries.
Overall, residual bubble breaking reflects the extent to which residents rely on cross-neighborhood mobility to overcome local amenity deficits, a dimension of spatial inequality that residence-based measures leave unobserved.

## Repository Structure
*   **`raw_data/`**: Contains raw input files (OD matrices, GRDI data, GADM, Street Networks, POIs). The data in this folder are dummy data, randomly generated to provide input for our analysis.
*   **`src/`**: Python scripts for data processing and generation.
*   **`data/`**: Directory where generated data will be saved. The subdirectories (`cities`, `pois`, `network`, `detour`, `tmp`, `population`)
## Execution Order

To demo the software on the provided synthetic dataset and reproduce the quantitative results and figures from the manuscript, execute the scripts sequentially from the root directory (e.g., `python src/01_get_data_population.py`). 
To run this analysis on your own mobility data, replace the synthetic files in the `raw_data/` directory with your own datasets. Ensure your Origin-Destination matrices match the column schema of the dummy data and are aggregated to the H3 resolution 7 global grid system. Update any relevant country, city boundary, or coordinate reference system configurations in the `src/` scripts before running the pipeline sequentially.
**Expected Run Time:** Executing the entire pipeline with real data (Scripts 1 through 15) on a standard desktop computer with 64 GB RAM takes approximately **6 to 8 hours**. The bulk of this time is dedicated to the shortest path routing calculations over the street networks (Scripts 6 and 7).

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
10.   **`10_descriptive_analysis.ipynb`**:
      *   Performs descriptive analysis, statistical tests, and visualizations. Output: Figure 1d, Figure 2, Supplementary Figures 2-4.
11.  **`11_city_analysis.ipynb`**:
     *   Performs descriptive analysis on the cities and do visualizations of compact vs. sparse cities. Output: Supplementary Figures 3, 5.
12.  **`12_slx_modeling.ipynb`**:
     *   Performs SLX modeling and plot the results. Output: Figures 3, Figures 4a-c, Supplementary Figure 6.
13.  **`13_poi_density_diversity.ipynb`**:
     *   Performs regression analysis to explore POI entropy vs. density and plot the results. Output: Figure 4d.
14.  **`14_covid_slx.ipynb`**:
     *   Performs SLX modeling and plot the results for the COVID case. Output: Supplementary Figure 7b.
15.  **`15_covid_identification_of_disconnected_cells.ipynb`**:
     *   Performs descriptive analysis on the cities under disruption (COVID), identifying disconnected cells. Output: Supplementary Figure 7a.

## Data Availability Statement
Please note that the files included in the**`raw_data/`** directory contain synthetic, randomly generated data provided solely to demonstrate the analysis pipeline. The actual datasets used in our research are sourced from:
* **Origin-Destination Matrices**: Made available from Cuebiq and the World Bank as part of the [NetMob 2024 Data Challenge](https://netmob.org/www24/) (Dataset hosted on the [World Bank Data Catalog](https://datacatalog.worldbank.org/search/dataset/0066094/aggregated-mobility-and-density-data-for-the-netmob-2024-data-challenge)). *(Citation: zhang2024netmob2024)*
* **OpenStreetMap**: Data is openly accessible via [openstreetmap.org](https://www.openstreetmap.org/).
* **NASA’s Global Gridded Relative Deprivation Index (GRDI)**: Retrieved from [SEDAC Columbia](https://sedac.ciesin.columbia.edu/data/set/povmap-grdi-v1).
* **Global Human Settlement**: Data was retrieved from the [GHSL website](https://ghsl.jrc.ec.europa.eu/).
* **Points of Interest (POIs)**: Retrieved from the [Overture Maps Foundation Places dataset](https://overturemaps.org/), derived from Meta and Microsoft products such as Bing Maps and Facebook pages.

## System Requirements

* **Operating System:** Tested on Ubuntu 22.04 LTS and macOS 14.0 (compatible with standard Linux/macOS/Windows environments).
* **Python Version:** Tested on Python 3.10 and 3.11.
* **Dependencies:** `pandas==2.1.0`, `geopandas==0.13.2`, `networkx==3.1`, `numpy==1.25.2`, `scipy==1.11.2`, `h3==3.7.6`, `shapely==2.0.1`, `rasterio==1.3.8`, `tqdm==4.66.1`, `pyyaml==6.0.1`, `haversine==2.8.0`, `igraph==0.10.8`. *(Note: Please verify these exact version numbers match your local environment).*
* **Non-Standard Hardware:** Due to the memory-intensive nature of large-scale shortest-path routing computations on OpenStreetMap road networks, running the full data generation pipeline requires a machine with at least **64 GB of RAM**.

## Installation Guide

1. **Clone this repository:**
   ```bash
   git clone https://github.com/RiegelGestr/ResidualBubbleBreakingNetmob24.git
   cd ResidualBubbleBreakingNetmob24
   ```

2. **Install the required packages via pip:**
   ```bash
   pip install -r requirements.txt
   ```

## Authors

- **Yuan Liao**, [website](https://yuan-liao.com).
- **Federico Delussu**, [website](https://scholar.google.com/citations?user=3yO7jOgAAAAJ&hl=it&oi=ao/).
- **Sílvia de Sojo**, [website](https://sdesojo.github.io/).
- **Laura Alessandretti**, [website](https://laura.alessandretti.com/).
- **Antonio Desiderio**, [website](https://antonioddesiderio.github.io).

## Questions and Support

For questions, issues, or requests related to this repository, please:
- Create an issue on the GitHub repository
- Contact the authors by email (in the paper)

## License

This project is licensed under the MIT License. See LICENSE file for details.
