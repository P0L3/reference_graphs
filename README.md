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
