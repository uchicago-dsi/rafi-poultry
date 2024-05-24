import gzip
import shutil


def save_file(gdf, filepath, file_format="geojson", gzip_file=False):
    if file_format == "geojson":
        final_filepath = filepath.with_suffix(".geojson")
        print(f"Saving file to {final_filepath}")
        gdf.to_file(f"{final_filepath}", driver="GeoJSON")
    elif file_format == "csv":
        final_filepath = filepath.with_suffix(".csv")
        print(f"Saving file to {final_filepath}")
        gdf.to_csv(f"{final_filepath}", index=False)
    else:
        raise ValueError("Unsupported file format. Use 'geojson' or 'csv'.")

    # gzip file for web
    if gzip_file:
        gzip_filepath = final_filepath.with_suffix(filepath.suffix + ".gz")
        print(f"Zipping file to {gzip_filepath}")
        with final_filepath.open("rb") as f_in:
            with gzip.open(gzip_filepath, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
