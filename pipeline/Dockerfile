# Use ARG to specify the platform (default is amd64)
ARG PLATFORM=linux/amd64

# Choose base image according to the platform
FROM --platform=${PLATFORM} osgeo/gdal:ubuntu-small-latest

# Update apt-get package
RUN apt-get -y update 

# Install Python and gdal dependencies
RUN apt -y install python3-pip libspatialindex-dev \
    && apt-get install -y --no-install-recommends \
       gdal-bin \
       libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY pipeline/requirements.txt .
RUN pip install --trusted-host pypi.python.org --no-cache-dir -r requirements.txt

# Copy the pipeline, notebook, and data directory into the container
COPY setup.py .
COPY pipeline ./pipeline
RUN pip install -e .

# Run the main.py script when the container launches
CMD ["python", "pipeline/main.py"]