""" post_process.py

    Handles the post processing required for the acquired lnb-capstone data
    

    Notes:
        - https://stackoverflow.com/questions/54120759/gmplot-api-issue
        - https://pypi.org/project/gmplot/
        - https://github.com/gmplot/gmplot/wiki
"""
import logging
import os
import sys
import time
from tkinter import filedialog
from typing import Dict, NewType, Union, List

import gmplot
import matplotlib.pyplot as plt
import pandas as pd

STRIKE_TIME = .5
EXCLUDE_DISTURBERS = True

color_dict = {
    "NODE1": (0, 0, 0),
    "NODE2": (255, 0, 0),
    "NODE3": (0, 255, 0),
    "NODE4": (255, 255, 0),
    "NODE5": (0, 0, 255),
    "NODE6": (255, 0, 255),
    "NODE7": (0, 255, 255),
    "NODE8": (255, 255, 255)
}


class Packet:
    """
    """
    gps_lat: float = 0
    gps_long: float = 0
    distance: int = 0

    def __init__(self, lat, lon, dis) -> None:
        self.gps_lat = lat
        self.gps_long = lon
        self.distance = dis

    def to_string(self):
        """ Prints a formatted string for debugging """
        return f"({self.gps_lat},{self.gps_long})-{self.distance}"

class Strike:
    """
    """
    utc: str = ""
    day: int = 0
    hour: int = 0
    minute: int = 0
    second: int = 0
    epoch: float = 0
    packet_list: List[Packet] = []

    def __init__(self, epoch: float) -> None:
        self.epoch = epoch
        timestruc: time.struct_time = time.localtime(epoch)
        self.utc = f"{timestruc.tm_year:4d}-{timestruc.tm_mon:2d}-{timestruc.tm_mday:2d}T{timestruc.tm_hour:2d}:{timestruc.tm_min:2d}:{timestruc.tm_sec:2d}Z"
        self.day = self.utc[8:10]
        self.hour = self.utc[11:13]

    def add_event(self, pack: Packet):
        self.packet_list.append(pack)

    def to_string(self):
        """ Prints a formatted string for debugging """
        stk = f"{self.utc}: "
        for pack in self.packet_list:
            stk += pack.to_string() + ","
        return stk

class PostProcess:
    """ Generates a basic set of graphics from input lightning data csvs

    Each dataset of CSVs should be contained within their own folder, the program will
    automatically prompt the user to select a dataset with a filedialog box. Afterwards, it will
    read in all the CSVs into a collective dataframe with the following labels:

    UTC_Time, Epoch_Time, GPS_Latitude, GPS_Longitude, Distance

    This cumulative dataframe will be sorted by timestamp, and then parsed to identify strikes from
    different sources. Each strike will be identified by a timestamp, and will contain a list of
    nodes that detected it, with the distance away from the node.

    Each object of Packet type will contain a gps latitude and longitude to identify the node, and
    a distance value to show the distance from the node.

    gps_lat, gps_long, distance

    The strike will be represented by the Strike class, which has a public utc timestamp, and a
    list of Packet objects described above.

    utc, packet_list
    """
    # Define class constants
    nodes = []
    strikes: List[Strike] = []
    dataset: str = ""
    start_time: float = 0
    end_time: float = 0
    timespan: float = 0
    sum_df = pd.DataFrame()

    def __init__(self) -> None:
        # Initialize Logger
        fmt_main = "%(asctime)s | %(levelname)s | LNB_Post:\t%(message)s"
        logging.basicConfig(format=fmt_main, level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")


        self.read_csvs()
        self.identify_strikes()

        logging.info("%d Strikes. Strike at %s has %d elements", len(self.strikes), self.strikes[0].utc, len(self.strikes[0].packet_list))
        logging.info("First strike: %s", self.strikes[1].to_string())

        if not os.path.exists(f"./outputs/{self.dataset}"):
            os.mkdir(f"./outputs/{self.dataset}")

        self.generate_bar()
        self.generate_scatter()
        self.generate_gmap()

    def read_csvs(self):
        """ Read in all the csvs in a directory

        Ideally all csvs in the directory are from the same storm and have similar time ranges

        TODO: add local timespans for better node graphs
        """
        # Select the dataset to read from, should just be a folder filled with csvs
        logging.info("Select storm directory")
        data_dir = filedialog.askdirectory()
        if data_dir == "":
            logging.error("No file specified! Exiting...")
            sys.exit(1)
        self.dataset = os.path.basename(data_dir)

        # Debugging
        logging.info("Dataset = %s", self.dataset)
        logging.debug("Contents = %s", os.listdir(data_dir))

        # Read in data from each file in the directory
        for datafile in os.listdir(data_dir):
            data_frame = pd.read_csv(filepath_or_buffer=data_dir+"/"+datafile, header=0)
            self.sum_df = pd.concat(objs=[self.sum_df, data_frame], ignore_index=True)

            # Append the gps coordinates for the first two elements
            self.nodes.append([data_frame["GPS_Latitude"][0], data_frame["GPS_Longitude"][0]])
            # The rest of the elements for each node will be tuples -> [Epoch_Time, Distance]
            num_elements = len(data_frame["Epoch_Time"])
            for i in range(num_elements):
                utc_tm = data_frame["UTC_Time"][i]
                tm_stp = data_frame["Epoch_Time"][i]
                stk_dist = data_frame["Distance"][i]

                # Set the min and max time identified from the dataset
                if i == 0 and tm_stp < self.start_time or self.start_time == 0:
                    self.start_time = tm_stp
                if i == num_elements-1 and tm_stp > self.end_time:
                    self.end_time = tm_stp

                # If this is a disturber, cap it at max distance
                if stk_dist > 40:
                    stk_dist = 40

                entry = [utc_tm,tm_stp,stk_dist]

                # Filter out disturbers, remove if statement (but keep append) to include disturbers
                if stk_dist < 40:
                    self.nodes[len(self.nodes)-1].append(entry)

            # Debugging info for timestamp ranges
            logging.info(
                "%s entry starts %s",
                datafile,
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))
            )
        # Shows the timestamp range of the dataset as a whole
        self.sum_df.sort_values(by="Epoch_Time", inplace=True, )

        # Debug
        timelist = self.sum_df["Epoch_Time"].to_numpy()
        logging.info("First time = %d", timelist[1])
        logging.info("Last time = %d", timelist[len(timelist)-2])

        self.timespan = self.end_time-self.start_time
        logging.info("Dataset spans %f hours", self.timespan/3600)

    def identify_strikes(self):
        """ Populates the strikes list with Strike objects


        """
        # The epoch time of the current strike
        ep1 = 0

        # Loop through each data entry and decide where to place it
        i = 0
        while i < len(self.sum_df):
            # The epoch time of the incoming packet
            ep2 = self.sum_df["Epoch_Time"].to_numpy()[i]

            # Create a new packet from the current entry
            pack = Packet(
                self.sum_df["GPS_Latitude"][i],
                self.sum_df["GPS_Longitude"][i],
                self.sum_df["Distance"][i]
            )

            # If enough time has passed from the previous strike, then create a new one
            if ep2-ep1 > STRIKE_TIME:
                ep1 = ep2
                self.strikes.append(Strike(ep1))

            # Add the packet data to the current Strike object
            self.strikes[len(self.strikes)-1].add_event(pack)
            i += 1

    def generate_bar(self):
        """ Generates a bar chart that shows how many strikes that were detected over a time period

            This should produce a 1 chart per day, with a bar for each hour showing strike count
            and 1 chart containing all data, with a bar for each day showing strike count

            Potential Future improvements:
                - Color code the bar to show difference between disturbers and strikes

            Args:
                - None
            Returns:
                - None
        """
        data = self.sum_df.to_numpy()

        hours = range(0,24)
        seconds_h = range(0,86400,3600)

        start_day = int(data[0][0][8:10])
        stop_day = int(data[len(data)-1][0][8:10])
        days = range(start_day,stop_day)
        seconds_d = range(0,(stop_day-start_day)*86400,86400)

        tot_tm: List[str] = []
        tot_stk: List[int] = []

        c = 0
        while c < len(data):
            day: int = int(data[c][0][8:10])
            daily_tm: List[str] = []
            daily_stk: List[int] = []

            while c < len(data) and int(data[c][0][8:10]) == day:
                # Acquire graphable time in seconds
                tm = int(data[c][0][17:19]) + int(data[c][0][14:16])*60 + int(data[c][0][11:13])*3600

                # Append data entries
                daily_tm.append(tm)
                tot_tm.append(tm + (start_day-int(data[c][0][8:10]))*86400)
                daily_stk.append(int(data[c][4]))
                tot_stk.append(int(data[c][4]))

                c += 1

            # Generate the daily plot
            plot_name = f"{self.dataset}_Strikes-per-Hour_day{day}"
            plt.bar(daily_tm, daily_stk, width=3600)
            plt.xlabel("Time Interval (sec)")
            plt.xticks(ticks=seconds_h, labels=hours)
            plt.ylabel("Strikes per Hour")
            plt.title(plot_name)
            plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
            plt.close()


        # Generate the Scatterplot for the entire dataset
        plot_name = f"{self.dataset}_Strikes-per-Day"
        plt.bar(tot_tm, tot_stk, width=86400)
        plt.xlabel("Strikes per Day")
        plt.xticks(ticks=seconds_d, labels=days)
        plt.ylabel("Strike Count")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        plt.close()


        # zones = 24
        # interval = self.timespan/zones
        # sum_stk = []
        # time_stk = []
        # for i in range(zones+1):
        #     sum_stk.append(0)
        #     time_stk.append(self.start_time+interval*i)

        # for node in self.nodes:
        #     local_stk = []
        #     for i in range(zones+1):
        #         local_stk.append(0)

        #     c = 2
        #     while c < len(node):
        #         scale = int((node[c][1]-self.start_time)/interval)

        #         sum_stk[scale] += 1
        #         local_stk[scale] += 1

        #         c += 1

        #     # Generate the daily plot
        #     plot_name = f"{self.dataset}_Strikes-per-Hour_({day})"
        #     bar = plt.bar(time_stk, local_stk, width=interval)
        #     plt.xlabel("Time Interval (sec)")
        #     plt.xticks(range(0,24))
        #     plt.ylabel("Strikes per Hour")
        #     plt.title(plot_name)
        #     plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        #     plt.close()

        # # Generate the Scatterplot for the entire dataset
        # plot_name = f"{self.dataset}_Strikes-per-Day"
        # bar = plt.bar(time_stk, local_stk, width=interval)
        # plt.xlabel("Day")
        # plt.ylabel("Strike Count")
        # plt.title(plot_name)
        # plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        # plt.close()

    def generate_scatter(self):
        """ Generates a selection of scatterplots of when lightning was detected and how far

            This should generate one scatterplot per node, and a scatterplot that includes
            all nodes in the current dataset.
        """
        # nodes: List[str] = []
        # c = 0
        # while c < len(data):
        #     gps = f"({data[c][2]},{data[c][3]})"
        #     try:
        #         n = nodes.index(gps)
        #     except ValueError:
        #         nodes.append(gps)
        #     c += 1
        # print(nodes)

        data = self.sum_df.to_numpy()

        hours = range(0,24)
        seconds_h = range(0,86400,3600)

        start_day = int(data[0][0][8:10])
        stop_day = int(data[len(data)-1][0][8:10])
        days = range(start_day,stop_day)
        seconds_d = range(0,(stop_day-start_day)*86400,86400)

        tot_tm: List[str] = []
        tot_stk: List[int] = []

        c = 0
        while c < len(data):
            day: int = int(data[c][0][8:10])
            daily_tm: List[str] = []
            daily_stk: List[int] = []

            while c < len(data) and int(data[c][0][8:10]) == day:
                # Acquire graphable time in seconds
                tm = int(data[c][0][17:19]) + int(data[c][0][14:16])*60 + int(data[c][0][11:13])*3600

                # Append data entries
                daily_tm.append(tm)
                tot_tm.append(tm + (start_day-int(data[c][0][8:10]))*86400)
                daily_stk.append(int(data[c][4]))
                tot_stk.append(int(data[c][4]))

                c += 1
                
            # Generate the Scatterplot from only the current node
            plot_name = f"{self.dataset}_Scatter_day{day}"
            plt.scatter(daily_tm, daily_stk)
            plt.xlabel("Time (sec)")
            plt.xticks(ticks=seconds_h, labels=hours)
            plt.ylabel("Distance (km)")
            plt.title(plot_name)
            plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
            plt.close()
            
        # Generate the Scatterplot for the entire dataset
        plot_name = f"{self.dataset}_Sum_Scatter"
        plt.scatter(tot_tm, tot_stk)
        plt.xlabel("Time (sec)")
        plt.xticks(ticks=seconds_d, labels=days)
        plt.ylabel("Distance (km)")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        plt.close()
        # Assemble the data into time
        # for strike in self.strikes:
        #     for packet in strike.packet_list:
            
        #     c = 0
        #     while c < len(node):
        #         sum_tm.append(node[c][1])
        #         day_tm.append(node[c][1])

        #         sum_sd.append(node[c][2])
        #         day_sd.append(node[c][2])
        #         c += 1

        #     # Generate the Scatterplot from only the current node
        #     plot_name = f"{self.dataset}_Scatter_({node[0]}_{node[1]})"
        #     plt.scatter(day_tm, day_sd)
        #     plt.xlabel("Time (sec)")
        #     plt.ylabel("Distance (km)")
        #     plt.title(plot_name)
        #     plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        #     plt.close()

        # Generate the Scatterplot for the entire dataset
        # plot_name = f"{self.dataset}_Sum_Scatter"
        # plt.scatter(data[], sum_sd, )
        # plt.xlabel("Time (sec)")
        # plt.ylabel("Distance (km)")
        # plt.title(plot_name)
        # plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        # plt.close()

    def generate_gmap(self):
        """ Generate the plot of all nodes with the range of strikes, using the Google Maps API

            This will take all of the nodes, and all of the strikes, mark their positions on the
            map using the gps coordinates, and draw a circle for each strike, with a radius equal
            to the distance detected by the sensor.
            The map will be centered on the OMB building, and be zoomed out to include about 40km
        """
        for strike in self.strikes:
            # Create the map plotter:
            # Mark the OMB building as the center of the map, zoom, and plot a range
            omb_loc = (30.61771327808669, -96.33664482193207)
            gmap = gmplot.GoogleMapPlotter(omb_loc[0], omb_loc[1], 10, apikey='')
            gmap.marker(omb_loc[0], omb_loc[1], color='cornflowerblue')
            gmap.circle(omb_loc[0], omb_loc[1], 40000, face_alpha=0)

            # Plot the values from each node
            for packet in strike.packet_list:
                gmap.marker(packet.gps_lat, packet.gps_long, color='red')
                gmap.circle(packet.gps_lat, packet.gps_long, packet.distance*1000, face_alpha=0)

            # Draw the map:
            logging.debug("Printing strike from: %s", strike.utc)
            gmap.draw(f'./outputs/{self.dataset}/strike_{strike.epoch}.html')

if __name__ == "__main__":
    PostProcess()
