"""Utility functions for the RAFI pipeline."""

import gzip
import shutil
from pathlib import Path

import geopandas as gpd


def save_file(
    gdf: gpd.GeoDataFrame,
    filepath: Path,
    file_format: str = "geojson",
    gzip_file: bool = False,
    index: bool = False,
) -> None:
    """Saves a GeoDataFrame to a specified file format and optionally compresses it with gzip.

    Args:
        gdf: The GeoDataFrame to save.
        filepath: The file path to save the file to.
        file_format: The format to save the file in, either 'geojson' or 'csv'.
        gzip_file: Whether to gzip the file after saving.
        index: Whether to include the index in the saved file.

    Raises:
        ValueError: If an unsupported file format is provided.
    """
    if file_format == "geojson":
        final_filepath = filepath.with_suffix(".geojson")
        print(f"Saving file to {final_filepath}")
        gdf.to_file(f"{final_filepath}", driver="GeoJSON")
    elif file_format == "csv":
        final_filepath = filepath.with_suffix(".csv")
        print(f"Saving file to {final_filepath}")
        gdf.to_csv(f"{final_filepath}", index=index)
    else:
        raise ValueError("Unsupported file format. Use 'geojson' or 'csv'.")

    # gzip file for web
    if gzip_file:
        gzip_filepath = final_filepath.with_suffix(filepath.suffix + ".gz")
        print(f"Zipping file to {gzip_filepath}")
        with final_filepath.open("rb") as f_in:
            with gzip.open(gzip_filepath, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
