# Pull base Docker image
# https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html#jupyter-scipy-notebook
FROM jupyter/scipy-notebook:python-3.9

# Create working directory
WORKDIR /app

# Install Python 3 packages
COPY notebooks/requirements.txt .
RUN mamba install --quiet --yes --file requirements.txt -c conda-forge

# Installing pipeline package
COPY setup.py .
COPY pipeline ./pipeline
RUN pip install -e .

# Copy notebooks folder
COPY notebooks ./notebooks