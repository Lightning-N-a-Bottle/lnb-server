""" post_process.py

    Handle all processing of the acquired data here

    Notes:
        - https://stackoverflow.com/questions/54120759/gmplot-api-issue
        - https://pypi.org/project/gmplot/
        - https://github.com/gmplot/gmplot/wiki
"""
import gmplot
import pandas as pd
from tkinter import filedialog

nodes = []

def read_csvs():
    """
    """
    print("Select storm directory")
    data_dir = filedialog.askdirectory()
    print(f"directory = {data_dir}")

    for datafile in data_dir:
        print(f"data file = {datafile}")
        df = pd.read_csv(datafile)


def generate_gmap():
    # Create the map plotter:
    apikey = '' # (your API key here)

    # Mark the OMB building as the center of the map, zoom, and plot a range
    omb_loc = (30.61771327808669, -96.33664482193207)
    gmap = gmplot.GoogleMapPlotter(omb_loc[0], omb_loc[1], 10, apikey=apikey)
    gmap.marker(omb_loc[0], omb_loc[1], color='cornflowerblue')
    gmap.circle(omb_loc[0], omb_loc[1], 40000, face_alpha=0)

    # TODO: Read in CSV data

    nodes = [
        (30, -96, 100, 200, 10000),
        (30, -95, 300, 500, 12000),
        (31, -95, 500, 250, 900),
        (31, -96, 300, 700, 14000)
    ]

    # Place markers on the map from the nodes
    for node in nodes:
        gmap.marker(node[0], node[1], color='red')

        c = 2
        while c < len(node):
            # Record a circle for each strike in range
            gmap.circle(node[0], node[1], node[c], face_alpha=0)
            c+=1

    # Draw the map:
    gmap.draw('map.html')

if __name__ == "__main__":
    read_csvs()
    generate_gmap()