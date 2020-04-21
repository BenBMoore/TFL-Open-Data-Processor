import configparser
import time

import pyproj
import requests
from pymongo import MongoClient


def get_approx_current_location(start_coord, end_coord, time_to_end_coord, approx_speed_kph):
    geodesic = pyproj.Geod(ellps='WGS84')
    fwd_azimuth, back_azimuth, line_distance = geodesic.inv(start_coord[0], start_coord[1], end_coord[0], end_coord[1])
    # Speed = distance/time  therefore speed * time(in seconds) = distance
    distance_away_from_end = (approx_speed_kph / (3.6)) * time_to_end_coord
    currlon, currlat, extra_bearing = geodesic.fwd(end_coord[0], end_coord[1], back_azimuth, distance_away_from_end)
    return [currlon, currlat]


def get_previous_station(station, destination, line, direction):
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]
    # Hard coded resolvers because TFL Arrvials API isn't correct.
    # Neasden showing up as a station for the met line, even though it isn't a met line station
    if station == "940GZZLUNDN" and line == "metropolitan":
        return "940GZZLUWYP"
    line_info = db.line_collection.find_one({"line_id": line, "direction": direction})
    # Iterate over line_info to find the correct naptan ids - first attempt destination check
    for routes in line_info["orderedLineRoutes"]:
        for index, value in enumerate(routes[1]["naptanIds"]):
            if value == station:
                return routes[1]["naptanIds"][index - 1]
     # Fallback to checking naptan ID's for previous station
     # for routes in line_info


def get_station_coord(station):
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]
    coords = db.station_collection.find_one({"_id": station})["coords"]
    return coords


def get_lineString_to_next_station(current_location, next_station_coords, time_to_next_station,
                                   chunks_to_generate_per_second):
    geodesic = pyproj.Geod(ellps='WGS84')
    lonlats = geodesic.npts(current_location[0], current_location[1], next_station_coords[0], next_station_coords[1],
                            time_to_next_station * chunks_to_generate_per_second)
    return lonlats


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
    # How many chunks per second to generate
    chunks_per_second = 2
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
                    # This ensures it's the closest station as arrivals returns all station arrivals for that train id
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
            current_location = previous_station_coords if "At" in current_location_text else get_approx_current_location(
                previous_station_coords, next_station_coords,
                time_to_next_station, 30)
            route_to_station = [previous_station_coords] if "At" in current_location_text else get_lineString_to_next_station(
                current_location, next_station_coords, time_to_next_station, chunks_per_second)
            time_generated = round(time.time() * 1000)


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
                "route": route_to_station,
                "timestamp": time_generated
            }
            train_collection.insert_one(train)
