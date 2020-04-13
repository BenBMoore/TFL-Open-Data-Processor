import configparser
import json
import sqlite3

import requests


def process_line_info():
    # Read API Info from config file
    config = configparser.ConfigParser()
    config.read("tfl_auth.ini")
    app_id = config['DEFAULT']['app_id']
    app_key = config['DEFAULT']['app_key']
    base_url = config['DEFAULT']['base_url']

    # Open SQLite connection
    conn = sqlite3.connect('example.db')
    c = conn.cursor()

    # Initial get all tube lines URL
    lines_given_mode_tube = 'Line/Mode/tube'
    # URL For Line Information
    line_info_given_tube_line = 'Line/{}/Route/Sequence/inbound'

    # Get line overview
    line_url = base_url + lines_given_mode_tube
    parameters = {'app_id': app_id, 'app_key': app_key}
    r = requests.get(line_url, params=parameters)

    line_info = r.json()
    # Iterate over each tube line
    for data in line_info:
        # Get Line Co-ords
        line_info_data = base_url + line_info_given_tube_line.format(data['id'])
        r = requests.get(line_info_data)
        line_data = r.json()
        # The array has to be imported as a json dump or SQLite will complain it doesn't conform to the blob data
        # type - will change once I decide on an actual db
        line_info = (data['id'], data['name'], json.dumps(line_data['lineStrings']))
        c.execute('insert into lines (id, name, line_coords) values (?, ?, ?)', line_info)
        conn.commit()
        # Gather stations on line
        for stations in line_data['stations']:
            station_name = stations['name']
            station_id = stations['id']
            station_coords = '[' + str(stations['lon']) + "," + str(stations['lat']) + ']'
            line_name = data['name']
            station_info = (station_id, station_name, station_coords, line_name)
            dupe_check = c.execute('SELECT line_name FROM stations WHERE ID Like ?', [station_id]).fetchone()

            if dupe_check is not None:
                c.execute('UPDATE stations SET line_name = ? WHERE id LIKE ?',
                          (dupe_check[0] + "," + line_name, station_id))
            else:
                c.execute('INSERT into stations (id, name, station_coords, line_name) values (?, ?, ?, ?)',
                          station_info)
                conn.commit()

    conn.close()
