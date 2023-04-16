""" post_process.py

    Handle all processing of the acquired data here

    Notes:
        - https://stackoverflow.com/questions/54120759/gmplot-api-issue
        - https://pypi.org/project/gmplot/
        - https://github.com/gmplot/gmplot/wiki
"""
import logging
import os
import sys
from tkinter import filedialog
import gmplot
import pandas as pd
import matplotlib.pyplot as plt
import time

nodes = []
dataset = ""
start_time = 0
end_time = 0
timespan = 0

def read_csvs():
    """
    """
    # Select the dataset to read from, should just be a folder filled with csvs
    logging.info("Select storm directory")
    data_dir = filedialog.askdirectory()
    logging.info("Directory = %s", data_dir)
    if data_dir == "":
        logging.error("No file specified! Exiting...")
        sys.exit(1)
    global dataset
    dataset = os.path.basename(data_dir)
    logging.debug("Contents = %s", os.listdir(data_dir))

    # Read in data from each file in the directory
    for datafile in os.listdir(data_dir):
        logging.debug("data file = %s", datafile)

        df = pd.read_csv(data_dir + "/" + datafile)

        # Append the gps coordinates for the first two, the rest of the elements will be tuples
        nodes.append(
            [
                df["GPS_Latitude"][0],
                df["GPS_Longitude"][0],
            ]
        )
        # The rest of the elements for each node will be tuples -> [Timestamp, Distance]
        for i in range(len(df["Timestamp"])):
            tm_stp = df["Timestamp"][i]
            stk_dist = df["Lightning Distance"][i]

            # Set the min and max time identified from the dataset
            global start_time, end_time
            if i == 0 and tm_stp < start_time or start_time == 0:
                start_time = tm_stp
            if i == len(df["Timestamp"])-1 and tm_stp > end_time:
                end_time = tm_stp

            # If this is a disturber, cap it at max distance
            if stk_dist > 40:
                stk_dist = 40

            entry = [tm_stp,stk_dist]

            # Filter out disturbers, remove if statement (but keep append) to include disturbers
            if stk_dist < 40:
                nodes[len(nodes)-1].append(entry)

        # Debugging info for timestamp ranges
        logging.info(
            "Entry starts %s",
            time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        )
    # Shows the timestamp range of the dataset as a whole
    global timespan
    timespan = (end_time-start_time)
    logging.info("Dataset spans %f hours", timespan/3600)

def generate_bar():
    """ Generates a bar chart that shows how many strikes that were detected over a time period

        This should have a configurable time-width per column.
        In addition, one bar chart should be generated per node, and one cumulative chart.
    """
    zones = 5
    interval = timespan/zones
    sum_stk = []
    time_stk = []
    for i in range(zones+1):
        sum_stk.append(0)
        time_stk.append(start_time+interval*i)

    for node in nodes:
        local_stk = []
        for i in range(zones+1):
            local_stk.append(0)

        c = 2
        while c < len(node):
            scale = int((node[c][0]-start_time)/interval)

            sum_stk[scale] += 1
            local_stk[scale] += 1

            c += 1

        # Generate the Scatterplot from only the current node
        plot_name = f"{dataset}_Strikes-over-time_({node[0]}_{node[1]})"
        plt.bar(time_stk, local_stk, width=interval)
        plt.xlabel("Time Interval (sec)")
        plt.ylabel("Strike Count")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{dataset}/{plot_name}.png")
        plt.show()

    # Generate the Scatterplot for the entire dataset
    plot_name = f"{dataset}_Strikes-over-time"
    plt.bar(time_stk, sum_stk, width=interval)
    plt.xlabel("Time Interval (sec)")
    plt.ylabel("Strike Count")
    plt.title(plot_name)
    plt.savefig(f"./outputs/{dataset}/{plot_name}.png")
    plt.show()
    plt.close()

def generate_scatter():
    """ Generates a selection of scatterplots of when lightning was detected and how far

        This should generate one scatterplot per node, and a scatterplot that includes
        all nodes in the current dataset.
    """
    sum_tm = []
    sum_sd = []

    # Organize the data from each node
    for node in nodes:
        local_tm = []
        local_sd = []

        c = 2
        while c < len(node):
            sum_tm.append(node[c][0])
            local_tm.append(node[c][0])

            sum_sd.append(node[c][1])
            local_sd.append(node[c][1])
            c += 1

        # Generate the Scatterplot from only the current node
        plot_name = f"{dataset}_Scatter_({node[0]}_{node[1]})"
        plt.scatter(local_tm, local_sd)
        plt.xlabel("Time (sec)")
        plt.ylabel("Distance (km)")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{dataset}/{plot_name}.png")
        plt.show()

    # Generate the Scatterplot for the entire dataset
    plot_name = f"{dataset}_Sum_Scatter"
    plt.scatter(sum_tm, sum_sd)
    plt.xlabel("Time (sec)")
    plt.ylabel("Distance (km)")
    plt.title(plot_name)
    plt.savefig(f"./outputs/{dataset}/{plot_name}.png")
    plt.show()
    plt.close()

def generate_gmap():
    """ Generate the plot of all nodes with the range of strikes, using the Google Maps API

        This will take all of the nodes, and all of the strikes, mark their positions on the
        map using the gps coordinates, and draw a circle for each strike, with a radius equal
        to the distance detected by the sensor.
        The map will be centered on the OMB building, and be zoomed out to include about 40km
    """
    # Create the map plotter:
    apikey = '' # (your API key here)

    # Mark the OMB building as the center of the map, zoom, and plot a range
    omb_loc = (30.61771327808669, -96.33664482193207)
    gmap = gmplot.GoogleMapPlotter(omb_loc[0], omb_loc[1], 10, apikey=apikey)
    gmap.marker(omb_loc[0], omb_loc[1], color='cornflowerblue')
    gmap.circle(omb_loc[0], omb_loc[1], 40000, face_alpha=0)

    # Example format for nodes, each row is gpslat, gpslong, [Time,Dist]...
    # nodes = [
    #     (30, -96, [0,100], [1,200], [2,10000]),
    #     (30, -95, [0,300], [1,500], [2,12000]),
    #     (31, -95, [0,500], [1,250], [2,900]),
    #     (31, -96, [0,300], [1,700], [2,14000])
    # ]

    # Place markers on the map from the nodes
    for node in nodes:
        gmap.marker(node[0], node[1], color='red')

        c = 2
        while c < len(node):
            # Record a circle for each strike in range
            gmap.circle(node[0], node[1], node[c][1]*1000, face_alpha=0)
            c+=1

    # Draw the map:
    gmap.draw(f'./outputs/{dataset}/map.html')

if __name__ == "__main__":
    fmt_main = "%(asctime)s | LNB_Post:\t%(message)s"
    logging.basicConfig(format=fmt_main, level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

    read_csvs()

    if not os.path.exists(f"./outputs/{dataset}"):
        os.mkdir(f"./outputs/{dataset}")

    generate_bar()
    generate_scatter()
    generate_gmap()
