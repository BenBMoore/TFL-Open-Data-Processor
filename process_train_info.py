import configparser
import datetime;

import pyproj
import requests
from pymongo import MongoClient


def get_approx_current_location(start_coord, end_coord, time_to_end_coord, approx_speed_kph):
    geodesic = pyproj.Geod(ellps='WGS84')
    fwd_azimuth, back_azimuth, line_distance = geodesic.inv(start_coord[0], start_coord[1], end_coord[0], end_coord[1])
    # Speed = distance/time  therefore speed * time(in seconds) = distance
    distance_away_from_end = (approx_speed_kph / (3.6)) * time_to_end_coord
    print(line_distance)
    print(distance_away_from_end)
    print(back_azimuth)
    currlon, currlat, extra_bearing = geodesic.fwd(end_coord[0], end_coord[1], back_azimuth, distance_away_from_end)
    return [currlon, currlat]


def get_previous_station(station, destination, line, direction):
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]

    line_info = db.line_collection.find_one({"line_id": line, "direction": direction})
    # Iterate over line_info to find the correct naptan ids
    for routes in line_info["orderedLineRoutes"]:
        for index, value in enumerate(routes[1]["naptanIds"]):
            if value == station:
                return routes[1]["naptanIds"][index - 1]


def get_station_coord(station):
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]
    coords = db.station_collection.find_one({"_id": station})["coords"]
    return coords


def populate_initial_train_info():
    # Read API Info from config file
    config = configparser.ConfigParser()
    config.read("tfl_auth.ini")
    app_id = config['DEFAULT']['app_id']
    app_key = config['DEFAULT']['app_key']
    base_url = config['DEFAULT']['base_url']
    parameters = {'app_id': app_id, 'app_key': app_key}
    # Open Mongo connection
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]
    db.train_collection.drop()
    train_collection = db["train_collection"]
    # URL For arrival predictions
    arrival_predictions_for_line = "Line/{}/Arrivals/"

    # Iterate over each line from DB
    for lines in db.line_collection.find({"direction": "inbound", }):
        arrival_predictions_data = base_url + arrival_predictions_for_line.format(lines["line_id"])
        r = requests.get(arrival_predictions_data, params=parameters)
        line_data = r.json()
        activeTrains = {}
        # Get active trains and "location" (API Returns all stations and predicted times, only want the train closest to stopping
        for trains in line_data:
            vehicle_id = str(trains["vehicleId"])
            time_to_station = trains["timeToStation"]
            line_id = trains["lineId"]
            station_id = trains["naptanId"]
            current_location = trains["currentLocation"]
            towards = trains.get("towards")
            # Seemingly optional entries
            destination_id = trains.get("destinationNaptanId")
            destination_name = trains.get("destinationName")
            direction = trains.get("direction")

            # If it's 000 it's a special service and we need to do something a bit different, still on the TODO
            # If it has no direction, cry (will probably have to fall back to the "towards" logic TODO
            # If it has no towards info (see front of train) check the platform it pulls into TODO
            if vehicle_id != "000" and direction is not None and (
                    towards is not None or towards != "See front of train"):
                if vehicle_id in activeTrains:
                    if activeTrains[vehicle_id]["time_to_station"] > time_to_station:
                        activeTrains[vehicle_id]["time_to_station"] = time_to_station
                        activeTrains[vehicle_id]["station_id"] = station_id
                else:
                    activeTrains[vehicle_id] = {}
                    activeTrains[vehicle_id]["time_to_station"] = time_to_station
                    activeTrains[vehicle_id]["line_id"] = line_id
                    activeTrains[vehicle_id]["station_id"] = station_id
                    activeTrains[vehicle_id]["current_location"] = current_location
                    activeTrains[vehicle_id]["destination_id"] = destination_id
                    activeTrains[vehicle_id]["line_id"] = line_id
                    activeTrains[vehicle_id]["direction"] = direction
                    activeTrains[vehicle_id]["towards"] = towards
                    activeTrains[vehicle_id]["destination_name"] = destination_name

        for k, v in activeTrains.items():
            next_station = v["station_id"]
            next_station_coords = get_station_coord(next_station)
            line = v["line_id"]
            direction = v["direction"]
            towards = v["towards"]
            destination_name = v["destination_name"]
            current_location_text = v["current_location"]
            previous_station = get_previous_station(next_station, destination_name, line, direction)
            previous_station_coords = get_station_coord(previous_station)
            time_to_next_station = v["time_to_station"]
            print("Start: " + previous_station)
            print(previous_station_coords)
            print("End: " + next_station)
            print(next_station_coords)
            current_location = previous_station_coords if "At" in current_location_text else get_approx_current_location(
                previous_station_coords, next_station_coords,
                time_to_next_station, 30)
            time_generated = datetime.datetime.now().timestamp()

            train = {
                "id": v['line_id'] + "-" + k,
                "timeToStation": v["time_to_station"],
                "destinationId": v["destination_id"],
                "direction": v["direction"],
                "currentLocation": current_location,
                "currentLocationText": current_location_text,
                "nextStation": next_station,
                "nextStationCoords": next_station_coords,
                "prevStation": previous_station,
                "prevStationCoords": previous_station_coords,
                "timestamp": time_generated
            }
            train_collection.insert_one(train)
