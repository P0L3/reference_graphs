# Docker initialization
1. Create Docker image from the folder containing [./Dockerfile](Dockerfile)
``` shell
docker build -t rel_dis:1.0 . 
```
> Takes approx. 820s

2. Run docker compose in the folder where [./docker-compose.yml](docker-compose.yml) is and open it in VS code:
``` shell
docker compose up
```
> Watch out for volume location, fix it accordingly

3. In VS Code install Container Dev and Jupyter extensions.

### Keyword graph

All analytics on data (without MDPI) are performed with [keyword_graph](REF_GRA/keyword_graph.ipynb), which includes:
1. Cleaning of the data and percentile, median and mean statistics
2. Filtering of data by mean length of keyword (clean outlayers)
3. Cooccurance graph construction
4. Centrality measures: Degree, Eigenvector

### Author graph


### TODO
