import configparser
import get_line_info
import process_train_info
import atexit
import os
import pprint
import time
from pymongo import MongoClient


def main():
    client = MongoClient('mongodb://localhost:27017/')
    db = client["train-database"]
    # No longer need to drop DB in testing, I'm fairly sure we've sorted out the masterdata
    db.drop_collection("line_collection")
    db.drop_collection("train_collection")
    db.drop_collection("station_collection")
    atexit.register(exit_handler)
    db_check = db.line_collection.find_one()
    if not db_check:
        get_line_info.process_line_info()
    print("Master Data Processed")
    while True:
        process_train_info.populate_initial_train_info()
        time.sleep(35)


def exit_handler():
    print("Goodbye!")
    # os.remove("example.db")


if __name__ == "__main__":
    main()
