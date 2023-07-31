# start with a base image - this defines the operating system, python version, etc
FROM python:3.9.16 AS builder

# set a directory for the app
WORKDIR /app

# copy requirements to the container
COPY ../pipeline/requirements.txt .
COPY ../notebooks/notebook_requirements.txt  .

RUN apt-get update && apt-get install -y \
  gdal-bin \
  python3-gdal \
  python3-pip

# install dependencies
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -r notebook_requirements.txt

# copies all of the files in your root of your project to /app in the Docker container
COPY ../pipeline/ .
COPY ../notebooks/ .
COPY ../data/ . 

# run the command to set up a jupyter notebook
CMD ["python", "main.py"]



