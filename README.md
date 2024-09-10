# RAFI Poultry
This project, in partnership with [RAFI-USA](https://rafiusa.org/), shows concentration in the poultry packaging industry.

The dashboard is displayed on [RAFI's site here](https://www.rafiusa.org/programs/challenging-corporate-power/poultry-barons-map/). Visit the site for more detail on the project and the background — this README will focus on the technical details of the project.

## Pipeline
The data pipeline for this project does the following:
- Joins records from [FSIS inspections](https://www.fsis.usda.gov/inspection/establishments/meat-poultry-and-egg-product-inspection-directory) with historical business data provided by NETS.
- Calculates 60 mile road distances from each plant in the FSIS records meeting our filtering criteria.
- Creates GeoJSONs for areas with access to one, two, or three plus poultry integrators.
- Filters poultry barns identified by a [computer vision model trained by Microsoft](https://github.com/microsoft/poultry-cafos) to reduce the number of false positives.

### Docker
The pipeline runs in Docker. If you use VS Code, this is set up to run in a [dev container](https://code.visualstudio.com/docs/devcontainers/containers), so build the container the way you normally would. Otherwise, just build the Docker image from the ```Dockerfile``` in the root of the directory.

If you are using the dev container, make sure that you change the ```PLATFORM``` variable in the ```devcontainer.json``` for your chip architecture:
```
"args": {
    "PLATFORM": "linux/arm64/v8" // Change this to "linux/amd64" on WSL and "linux/arm64/v8" on M1
}
```

### Data Files
Download the following files into the appropriate locations. **Note that permission is required to access the DSI Google Drive.**
- Example FSIS data is located in the DSI Google Drive: [MPI Directory by Establishment Name](https://drive.google.com/file/d/1A9CQqe-iXdFPXQ19WCKdtMNvZy7ypkym/view?usp=sharing) | [Establishment Demographic Data](https://drive.google.com/file/d/1FFtM-F0FSUgJfe39HgIXJtdRwctkG-q5/view?usp=sharing)
    - Save both files to ```data/raw/```
    - You can also download new data from the [FSIS Inspection site](https://www.fsis.usda.gov/inspection/establishments/meat-poultry-and-egg-product-inspection-directory). Just [update the filepaths config file](#using-different-files)
- [NETS data]((https://drive.google.com/drive/folders/1ayKn9SdtrIAO-q8AU9ScmuBK8Qv9ZlbS?usp=drive_link)) is located in the DSI Google Drive. Download this to ```data/raw/``` and save in a directory called ```nets```
- Download the [raw barns predictions for the entire USA](https://drive.google.com/file/d/1F-xhb9MxgJ5HKuEZho_luzDhqPtxOLY2/view?usp=sharing) from the DSI Google Drive and save to ```data/raw/```
- Barn filtering shapefiles: Download the [zip of all of the shapefiles](https://drive.google.com/file/d/1GSRM05ABDRXLUqmLqU_f-kI5yP8pSoqu/view?usp=sharing) from Google Drive and extract to ```data/shapefiles```. The sources for these shapefiles are listed in ```pipeline/rafi/config_geo_filters.yaml```.

### Using Different Files
If you are using different files (particularly for the FSIS data), just update the filenames in ```pipeline/rafi/config_filepaths.yaml```. Make sure the files are in the expected folder.

### API Keys
The pipeline uses [Mapbox](https://www.mapbox.com/) to calculate driving distances from the plants and expects a Mapbox API key located in a ```.env``` file saved to the root of the directory:

```
MAPBOX_API=yOuRmApBoXaPiKey
```

### Running the Pipeline
After all of the files and API keys are in place, run the pipeline:

```
python pipeline/pipelinve_v2.py
```

Cleaned data files will be output in a run folder in ```data/clean/```. To update the files displayed on the dashboard, follow the instuctions in [Updating the Dashboard Data](#updating-the-dashboard-data)

Note: You can also run each step of the pipline independently. Just make sure that the input files are available as expected in  ```__main__``` for each script.

## Dashboard
This is a [Next.js](https://nextjs.org/) project.

### Running the Dashboard
To run the dashboard locally (do **not** use the dev container!):

Install packages:
```bash
npm install
```

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Deplying the Dashboard
The dashboard is deployed via Vercel and is hosted on RAFI's site in an iframe.

Any update to the ```main``` branch of this repo will update the production deployment of the dashboard.

### Updating the Dashboard Data
If you rerun the pipeline, you need to update data files in both Google Cloud Storage and the files packaged with the Vercel deployment from GitHub.

#### Google Cloud Storage
The dashboard pulls data from Google Cloud Storage via an API. Upload the following files to the root of the ```rafi-poultry``` storage bucket in the ```rafi-usa``` project in the DSI account:
- ```barns.geojson.gz```
- ```plants.geojson```

#### Packaged Files
The dashboard loads the isochrones files showing captured areas from ```dashboard/public/data/v2/isochrones.geojson.gz```

### Dashboard Structure

#### Data
The dashboard loads data in ```lib/data.js```. This loads the packaged data and the Google Cloud Storage data via API calls.

Data is managed in ```lib/state.js``` and ```lib/useMapData.js```

Both the NETS data and farmer locations are sensitive, so those data files are processed behind api routes located in ```api/```.

#### Components
The dashboard consists primarily of a map component and a summary stats component.

The map logic lives in ```components/DeckGLMap.js``` and ```components/ControlPanel.js``` and the summary stats logic lives in ```components/SummaryStats.js``` and the sub-components.
