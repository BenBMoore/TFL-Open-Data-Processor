import configparser

import requests
from pymongo import MongoClient
from bson.json_util import loads


def process_line_info():
    # Read API Info from config file
    config = configparser.ConfigParser()
    config.read("tfl_auth.ini")
    app_id = config['DEFAULT']['app_id']
    app_key = config['DEFAULT']['app_key']
    base_url = config['DEFAULT']['base_url']

    # Open Mongo connection
    mongo_url = config['DEFAULT']['mongo_url']
    client = MongoClient(mongo_url)
    db = client["train-database"]
    # Initial get all tube lines URL
    lines_given_mode_tube = 'Line/Mode/tube'
    # URL For Line Information
    line_info_given_tube_line = 'Line/{}/Route/Sequence/{}'
    line_direction = ["inbound", "outbound"]
    # Stop Points for line
    line_stop_points = 'Line/{}/StopPoints'
    # Get line overview
    line_url = base_url + lines_given_mode_tube
    parameters = {'app_id': app_id, 'app_key': app_key}
    r = requests.get(line_url, params=parameters)

    line_info = r.json()
    # Iterate over each tube line
    for data in line_info:
        # Get Line Co-ords
        for direction in line_direction:
            line_info_data = base_url + line_info_given_tube_line.format(data['id'], direction)
            r = requests.get(line_info_data, params=parameters)
            line_data = r.json()
            routes = [[{"name": x['name'].replace("&harr;", "to")}, {"naptanIds": x['naptanIds']}] for x in
                      line_data['orderedLineRoutes']]
            line = {
                "line_id": line_data['lineId'],
                "direction": line_data['direction'],
                "lineStrings": line_data['lineStrings'],
                "orderedLineRoutes": routes
            }

            line_collection = db["line_collection"]
            line_collection.insert_one(line)
            station_collection = db["station_collection"]

        line_stop_points_data = base_url + line_stop_points.format(data['id'])
        r = requests.get(line_stop_points_data, params=parameters)
        stop_points_data = r.json()
        for stations in stop_points_data:
            if stations["stationNaptan"] == "HUBEAL":
                print("Wtf")
            station = {
                "_id": stations["stationNaptan"],
                "name": stations["commonName"],
                "coords": (stations["lon"], stations["lat"])
            }
            doc_count = station_collection.count_documents({"_id": station["_id"]})
            if doc_count == 0:
                station_collection.insert_one(station)
        # The array has to be imported as a json dump or SQLite will complain it doesn't conform to the blob data
        # type - will change once I decide on an actual db
        # Gather stations on line
