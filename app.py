import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import joblib
from fiona.crs import from_epsg
from flask import Flask
from flask import render_template, request, jsonify

app = Flask(__name__)

def buffer_segment(segment):
    segment_2263 = segment.copy()
    segment_2263.crs = from_epsg(4326)
    segment_2263 = segment_2263.to_crs(epsg=2263)
    segment_2263  = segment_2263.buffer(900)
    segment_buffer_4326 = segment_2263.to_crs(epsg=4326)
    return segment_buffer_4326


# index webpage displays cool visuals and receives user input text for model
@app.route('/')
@app.route('/index')
def index():

    # render web page with plotly graphs
    return render_template('master.html')

@app.route('/results', methods=['GET','POST'])
def results():
    data = request.get_json()
    print(data)
    return buffer_segment(gpd.GeoSeries([polygon])).to_json()

def main():
    app.run(host=app.config.get("HOST", "localhost"),port=app.config.get("PORT", 9000))

if __name__ == '__main__':
    main()
