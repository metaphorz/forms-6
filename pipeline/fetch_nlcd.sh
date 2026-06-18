#!/bin/zsh
# Fetch NLCD 2021 Land Cover GeoTIFF clip for the grid bbox from the MRLC WCS.
# Properly georeferenced (EPSG:4326), used by build_roughness.py.
cd "$(dirname "$0")/.."
mkdir -p data
BASE="https://www.mrlc.gov/geoserver/ows"
# bbox covers the 840-vertex grid with margin: lon[-81.95,-79.95] lat[25.60,26.55]
URL="${BASE}?service=WCS&version=2.0.1&request=GetCoverage"
URL+="&coverageId=mrlc_download__NLCD_2021_Land_Cover_L48&format=image/tiff"
URL+="&subsettingCrs=http://www.opengis.net/def/crs/EPSG/0/4326"
URL+="&outputCrs=http://www.opengis.net/def/crs/EPSG/0/4326"
URL+="&subset=Lat(25.60,26.55)&subset=Long(-81.95,-79.95)"
echo "Fetching NLCD 2021 clip -> data/nlcd_grid.tif"
curl -s --max-time 180 "$URL" -o data/nlcd_grid.tif -w "http=%{http_code} bytes=%{size_download} type=%{content_type}\n"
file data/nlcd_grid.tif
