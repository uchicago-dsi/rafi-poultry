# Use ARG to specify the platform (default is amd64)
# Note: this is set to match the machine with the Make command make build-pipeline
ARG PLATFORM=linux/amd64

# Dynamically choose correct base image based on platform
FROM --platform=${PLATFORM} osgeo/gdal:ubuntu-full-3.6.3

# Install Python and gdal dependencies
RUN apt-get -y update 
RUN apt -y install python3-pip libspatialindex-dev \
    && apt-get install -y --no-install-recommends \
       gdal-bin \
       libgdal-dev \
       git \
       openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY pipeline/requirements.txt .
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

# Copy the pipeline, notebook, and data directory into the container
# COPY setup.py .
COPY pyproject.toml .
COPY setup.py .
COPY pipeline ./pipeline
RUN pip install -e .

# Set environment variable for pipeline logic
ENV INSIDE_DOCKER=True

CMD ["bin/bash"]