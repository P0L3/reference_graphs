FROM jupyter/pyspark-notebook:python-3.8

WORKDIR /rel_dis

COPY ./requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

RUN mkdir REL_DIS

CMD ["echo", "REL_DIS container ready!"]
