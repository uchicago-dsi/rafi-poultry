#Use python 3.9 as the base image
FROM --platform=linux/arm64 osgeo/gdal:ubuntu-full-3.6.3

RUN apt-get -y update 

RUN apt -y install python3-pip libspatialindex-dev \
    && apt-get install -y --no-install-recommends \
       gdal-bin \
       libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

#Set the working directory
WORKDIR /app

#Install any needed packages specified in requirements.txt
COPY pipeline/requirements.txt .
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

COPY notebooks/notebook_requirements.txt .
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r notebook_requirements.txt

#Copy the pipeline, notebook, and data directory into the container
COPY pipeline/ ./pipeline
COPY notebooks ./notebooks

#Run the main.py script when the container launches
CMD ["python", "pipeline/main.py"]












