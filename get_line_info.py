import configparser
import requests
import sqlite3
import json


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
    # URL For Line coordinates
    line_coords_given_tube_line = 'Line/{}/Route/Sequence/inbound'

    # Get line overview
    line_url = base_url + lines_given_mode_tube
    parameters = {'app_id': app_id, 'app_key': app_key}
    r = requests.get(line_url, params=parameters)

    line_info = r.json()
    for data in line_info:
        # Get Line Co-ords
        line_coords_url = base_url + line_coords_given_tube_line.format(data['id'])
        r = requests.get(line_coords_url)
        line_coords_data = r.json()
        # Remove Duplicate Coords

        # The array has to be imported as a json dump or SQLite will complain it doesn't conform to the blob data type
        info = (data['id'], data['name'], json.dumps(line_coords_data['lineStrings']))
        c.execute('insert into lines (id, name, line_coords) values (?, ?, ?)', info)
        conn.commit()

    conn.close()
