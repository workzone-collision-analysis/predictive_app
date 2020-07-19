import json
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString
from joblib import dump, load
from fiona.crs import from_epsg
from flask import Flask
from flask import render_template, request, jsonify

app = Flask(__name__)

model = load('models/model.pkl')
scaler = load('models/scaler.pkl')

columns=['posted_speed',
       'street_width',
       'daylight_ratio',
       'peak_ratio',
       'season_fall',
       'season_spring',
       'season_summer',
       'season_winter',
       'roadway_type_1',
       'roadway_type_2',
       'roadway_type_3',
       'roadway_type_4',
       'roadway_type_9',
       'create_time_weekend_0',
       'create_time_weekend_1']

numerical_features = ['posted_speed', 'street_width', 'daylight_ratio', 'peak_ratio' ]

def buffer_segment(segment):
    segment_2263 = gpd.GeoSeries(segment)
    segment_2263.crs = from_epsg(4326)
    segment_2263 = segment_2263.to_crs(epsg=2263)
    segment_2263  = segment_2263.buffer(900)
    segment_buffer_4326 = segment_2263.to_crs(epsg=4326)
    return segment_buffer_4326


# below functions were from https://github.com/workzone-collision-analysis/capstone/blob/master/notebooks/511_04_data_processing_for_clustering.ipynb

def calculate_day_duration(x):
    temporal_range = pd.date_range(start = x.create_time.replace(hour=0, minute=0, second=0),
                                   end = x.close_time.replace(hour=23, minute=59, second=0),
                                   freq='T')
    duration_list = [1 if t>x.create_time and t<=x.close_time else 0 for t in temporal_range]
    day_duration_temporal_range = [1 if (t.hour>=6 and t.hour<18) else 0 for t in temporal_range]
    return np.dot(np.array(duration_list), np.array(day_duration_temporal_range))/60


def calculate_peak_duration(x):
    temporal_range = pd.date_range(start = x.create_time.replace(hour=0, minute=0, second=0),
                                   end = x.close_time.replace(hour=23, minute=59, second=0),
                                   freq='T')
    duration_list = [1 if t>x.create_time and t<=x.close_time else 0 for t in temporal_range]
    peak_duration_temporal_range = [1 if (t.hour>=7 and t.hour<9) or (t.hour>=16 and t.hour<18) else 0 for t in temporal_range]
    return np.dot(np.array(duration_list), np.array(peak_duration_temporal_range))/60

def season(x):
    if x.month==4 or x.month==5:
        return 'spring'
    elif x.month >=6 and x.month <= 9:
        return 'summer'
    elif x.month == 10 or x.month==11:
        return 'fall'
    else:
        return 'winter'

def is_weekday(x):
    if x.weekday() == 5 or x.weekday() == 6:
        return 1
    else:
        return 0


crash_rate = {0:16.04,
              1:13.10,
              2:13.85,
              3:16.48}

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
    df_511 = pd.DataFrame(index=[0])
    df_511['create_time'] = pd.to_datetime(data['create_date'] +' '+ data['create_time'])
    df_511['close_time'] = pd.to_datetime(data['close_date'] +' '+ data['close_time'])
    create_season = df_511['create_time'].apply(lambda x:season(x)).tolist()[0]
    create_weekday = df_511['create_time'].apply(lambda x:is_weekday(x)).tolist()[0]
    df_511['duration'] = df_511['close_time'] -  df_511['create_time']
    df_511['duration'] = pd.to_timedelta(df_511['duration'],unit='h')
    df_511['duration'] = df_511['duration']/np.timedelta64(1, 'h')

    if df_511['duration'].tolist()[0]>24:
        df_511['duration'] = 'Error'

    df_511['peak_duration'] = df_511.apply(lambda x:calculate_peak_duration(x), axis=1)
    df_511['daytime_duration'] = df_511.apply(lambda x:calculate_day_duration(x), axis=1)
    df_511['daylight_ratio'] = df_511['daytime_duration'] / df_511['duration']
    df_511['peak_ratio'] = df_511['peak_duration'] / df_511['duration']

    df_511_clustering = df_511[['daylight_ratio','peak_ratio']].copy()
    df_511_clustering['posted_speed'] = data['posted_speed']
    df_511_clustering['street_width'] = data['street_width']
    df_511_clustering[numerical_features] = scaler.transform(df_511_clustering[numerical_features])

    if create_season == 'spring':
        df_511_clustering['season_fall'] = 0
        df_511_clustering['season_spring'] = 1
        df_511_clustering['season_summer'] = 0
        df_511_clustering['season_winter'] = 0
    elif create_season == 'summer':
        df_511_clustering['season_fall'] = 0
        df_511_clustering['season_spring'] = 0
        df_511_clustering['season_summer'] = 1
        df_511_clustering['season_winter'] = 0
    elif create_season == 'fall':
        df_511_clustering['season_fall'] = 1
        df_511_clustering['season_spring'] = 0
        df_511_clustering['season_summer'] = 0
        df_511_clustering['season_winter'] = 0
    elif create_season == 'winter':
        df_511_clustering['season_fall'] = 0
        df_511_clustering['season_spring'] = 0
        df_511_clustering['season_summer'] = 0
        df_511_clustering['season_winter'] = 1

    if data['roadway_type'] == 'Street':
        df_511_clustering['roadway_type_1'] = 1
        df_511_clustering['roadway_type_2'] = 0
        df_511_clustering['roadway_type_3'] = 0
        df_511_clustering['roadway_type_4'] = 0
        df_511_clustering['roadway_type_9'] = 0

    elif data['roadway_type'] == 'Highway':
        df_511_clustering['roadway_type_1'] = 0
        df_511_clustering['roadway_type_2'] = 1
        df_511_clustering['roadway_type_3'] = 0
        df_511_clustering['roadway_type_4'] = 0
        df_511_clustering['roadway_type_9'] = 0

    elif data['roadway_type'] == 'Bridge':
        df_511_clustering['roadway_type_1'] = 0
        df_511_clustering['roadway_type_2'] = 0
        df_511_clustering['roadway_type_3'] = 1
        df_511_clustering['roadway_type_4'] = 0
        df_511_clustering['roadway_type_9'] = 0

    elif data['roadway_type'] == 'Tunnel':
        df_511_clustering['roadway_type_1'] = 0
        df_511_clustering['roadway_type_2'] = 0
        df_511_clustering['roadway_type_3'] = 0
        df_511_clustering['roadway_type_4'] = 1
        df_511_clustering['roadway_type_9'] = 0

    elif data['roadway_type'] == 'Ramp':
            df_511_clustering['roadway_type_1'] = 0
            df_511_clustering['roadway_type_2'] = 0
            df_511_clustering['roadway_type_3'] = 0
            df_511_clustering['roadway_type_4'] = 0
            df_511_clustering['roadway_type_9'] = 1
    else:
        df_511_clustering['roadway_type_1'] = 'ERROR'

    if create_weekday == 0:
            df_511_clustering['create_time_weekend_0'] = 1
            df_511_clustering['create_time_weekend_1'] = 0

    else:
            df_511_clustering['create_time_weekend_0'] = 0
            df_511_clustering['create_time_weekend_1'] = 1

    clustering_result = model.predict(df_511_clustering[columns])
    print(clustering_result)
    polygon = buffer_segment(LineString(data['coords']))
    gdf_511 = gpd.GeoDataFrame(df_511[['duration',
                                        'peak_duration',
                                        'create_time',
                                        'close_time']], geometry=polygon)
    gdf_511['create_time'] = gdf_511['create_time'].astype(str)
    gdf_511['close_time'] = gdf_511['close_time'].astype(str)
    gdf_511['cluster'] = clustering_result[0]
    gdf_511['crash_rate'] = crash_rate[clustering_result[0]]
    return gdf_511.to_json()

def main():
    app.run()

if __name__ == '__main__':
    main()
