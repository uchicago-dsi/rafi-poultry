# Define constants

# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
pipeline_image_name := "rafi-pipeline"
pipeline_container_name := "rafi-pipeline-container"
pipeline_dir := "$(current_abs_path)pipeline"

# notebook constants
notebooks_image_name := "rafi-notebooks"
notebooks_container_name := "rafi-notebooks-container"
notebooks_dir := "$(current_abs_path)notebooks"

# Detect architecture
ARCH := $(shell uname -m)
ifeq ($(ARCH),x86_64)
    DOCKER_PLATFORM=linux/amd64
else ifeq ($(ARCH),arm64)
    DOCKER_PLATFORM=linux/arm64/v8
else
    $(error Unsupported architecture)
endif

# environment variables
include .env

# Build Docker image for pipeline
# TODO: probably just want to delete this and use the pipeline image in the pipeline container
build-pipeline:
	docker build --platform $(DOCKER_PLATFORM) -t $(pipeline_image_name) -f "${pipeline_dir}/Dockerfile" $(current_abs_path) --build-arg PLATFORM=$(DOCKER_PLATFORM)

# Run pipeline image with interactive terminal
run-pipeline-bash:
	docker run -e "MAPBOX_API=${MAPBOX_API}" -it -v $(current_abs_path)data:/app/data $(pipeline_image_name) /bin/bash 

# Run pipeline image with arguments
# TODO: Should this actually be how we set up args for this?
run-pipeline:
	docker run -e "MAPBOX_API=${MAPBOX_API}" -v $(current_abs_path)data:/app/data $(pipeline_image_name) python pipeline/main.py $(args)

# Build Docker image for notebooks
build-notebooks:
	docker build --platform $(DOCKER_PLATFORM) -t $(notebooks_image_name) -f "${notebooks_dir}/Dockerfile" $(current_abs_path) --build-arg PLATFORM=$(DOCKER_PLATFORM)

# Run notebooks
run-notebooks:
	docker run -v $(current_abs_path)data:/app/data -v $(notebooks_dir)/:/app/notebooks \
	--name $(notebooks_container_name) --rm -p 8888:8888 -t $(notebooks_image_name) jupyter lab --port=8888 --ip='*' \
	--NotebookApp.token='' --NotebookApp.password='' --no-browser --notebook-dir=/app/notebooks --allow-root