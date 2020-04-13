import configparser
import get_line_info
import sqlite3
import atexit
import os


def main():
    atexit.register(exit_handler)
    print("Starting up!")
    print("Performing initial tasks")
    print("Download Line Info from TFL")
    if os.path.exists("example.db"):
        os.remove("example.db")
        print("Old data removed")
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    # Will probably keep masterdata once it has been downloaded
    c.execute('''CREATE TABLE lines
                (id TEXT, name TEXT, line_coords BLOB)''')
    c.execute('''CREATE TABLE stations
                (id TEXT, name TEXT, station_coords TEXT, line_name TEXT)''')
    conn.commit()
    conn.close()
    get_line_info.process_line_info()


def exit_handler():
    print("Goodbye!")
    # os.remove("example.db")


if __name__ == "__main__":
    main()
