# RAFI-USA: Concentration in the Meat-Packing Industry
Name: Stella Chen
Email: stellaqc@uchicago.edu

## Context

This project is in partnership between the Data Science Institude of University of Chicago and the nonprofit organization RAFI-USA. This repository contains scripts and notebooks for performing cleaning, data analysis, and visualization of various datasets for processing plants,  farms, and businesses across the US. 

## Directories

- Notebooks
    - Contains Jupyter Notebooks for EDA, visualization, and short analysis.
- Pipeline
    - Contains Python scripts to clean, merge, and produce new data that will be served by the dashboard based on datasets.
    - Utils
        - A Python package with modules containing analysis and visualization functions that can be imported for use in Jupyter notebooks or Python scripts. 

## Development Dependencies

- Docker
- Make

## Setup

(1) Install [Docker](https://docker-curriculum.com/) if you have not already done so. Windows users
will have to set up and configure Windows Subsystem for Linux ([WSL2](https://docs.microsoft.com/en-us/windows/wsl/install))
beforehand.

(2) Install `make` for MacOS or Linux.  For example, users with Ubuntu would run `sudo apt update` followed by `sudo apt install make`. Confirm correct installation by running the command `make --version`.

(3) Ensure that Docker is running. Then navigate to the root of the project and run the command `make build` to create a new Docker image.

(4) Make File Commands/Instructions:
- ```make build-pipeline``` will build the Docker image for the pipeline scripts
- ```make run-pipeline-bash``` will run the Docker container from the pipeline image with interactive terminal
- ```make run-pipeline``` will run the Docker container from the pipeline image
- ```make build-notebooks``` will build the Docker image for the notebooks to be run in Jupyter lab
- ```run-notebooks``` will build the Docker image for the Jupyter notebooks
- ```run-notebooks``` will run the Docker container from the notebooks image
