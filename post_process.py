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
import time
import gmplot
import pandas as pd
import matplotlib.pyplot as plt


class PostProcess:
    """ Generates a basic set of graphics from 
    
    """
    def __init__(self) -> None:
        # Initialize Logger
        fmt_main = "%(asctime)s | LNB_Post:\t%(message)s"
        logging.basicConfig(format=fmt_main, level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")

        # Define class constants
        self.nodes = []
        self.dataset = ""
        self.start_time = 0
        self.end_time = 0
        self.timespan = 0
        self.sum_df = pd.DataFrame()

        self.read_csvs()

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
        logging.info("Directory = %s", self.dataset)
        logging.debug("Contents = %s", os.listdir(data_dir))

        # Read in data from each file in the directory
        for datafile in os.listdir(data_dir):
            data_frame = pd.read_csv(data_dir + "/" + datafile)
            self.sum_df = pd.concat([self.sum_df, data_frame])

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
                # if stk_dist < 40:
                self.nodes[len(self.nodes)-1].append(entry)

            # Debugging info for timestamp ranges
            logging.info(
                "%s entry starts %s",
                datafile,
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))
            )
        # Shows the timestamp range of the dataset as a whole
        self.sum_df.sort_values("Epoch_Time")
        self.timespan = self.end_time-self.start_time
        logging.info("Dataset spans %f hours", self.timespan/3600)

    def generate_bar(self):
        """ Generates a bar chart that shows how many strikes that were detected over a time period

            This should have a configurable time-width per column.
            In addition, one bar chart should be generated per node, and one cumulative chart.
        """
        zones = 24
        interval = self.timespan/zones
        sum_stk = []
        time_stk = []
        for i in range(zones+1):
            sum_stk.append(0)
            time_stk.append(self.start_time+interval*i)

        for node in self.nodes:
            local_stk = []
            for i in range(zones+1):
                local_stk.append(0)

            c = 2
            while c < len(node):
                scale = int((node[c][1]-self.start_time)/interval)

                sum_stk[scale] += 1
                local_stk[scale] += 1

                c += 1

            # Generate the Scatterplot from only the current node
            # Generate the daily plot
            plot_name = f"{self.dataset}_Strikes-over-time_({node[0]}_{node[1]})"
            plt.bar(time_stk, local_stk, width=interval)
            plt.xlabel("Time Interval (sec)")
            plt.ylabel("Strike Count")
            plt.title(plot_name)
            plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
            plt.close()

        # Generate the Scatterplot for the entire dataset
        plot_name = f"{self.dataset}_Strikes-over-time"
        plt.xlabel("Time Interval (sec)")
        plt.ylabel("Strike Count")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        plt.close()

    def generate_scatter(self):
        """ Generates a selection of scatterplots of when lightning was detected and how far

            This should generate one scatterplot per node, and a scatterplot that includes
            all nodes in the current dataset.
        """
        sum_tm = []
        sum_sd = []

        # Organize the data from each node
        for node in self.nodes:
            local_tm = []
            local_sd = []

            c = 2
            while c < len(node):
                sum_tm.append(node[c][1])
                local_tm.append(node[c][1])

                sum_sd.append(node[c][2])
                local_sd.append(node[c][2])
                c += 1

            # Generate the Scatterplot from only the current node
            plot_name = f"{self.dataset}_Scatter_({node[0]}_{node[1]})"
            plt.scatter(local_tm, local_sd)
            plt.xlabel("Time (sec)")
            plt.ylabel("Distance (km)")
            plt.title(plot_name)
            plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
            plt.close()

        # Generate the Scatterplot for the entire dataset
        plot_name = f"{self.dataset}_Sum_Scatter"
        plt.scatter(sum_tm, sum_sd)
        plt.xlabel("Time (sec)")
        plt.ylabel("Distance (km)")
        plt.title(plot_name)
        plt.savefig(f"./outputs/{self.dataset}/{plot_name}.png")
        plt.close()

    def generate_gmap(self):
        """ Generate the plot of all nodes with the range of strikes, using the Google Maps API

            This will take all of the nodes, and all of the strikes, mark their positions on the
            map using the gps coordinates, and draw a circle for each strike, with a radius equal
            to the distance detected by the sensor.
            The map will be centered on the OMB building, and be zoomed out to include about 40km
        """
        # Example format for nodes, each row is gpslat, gpslong, [Time,Dist]...
        # nodes = [
        #     (30, -96, [0,100], [1,200], [2,10000]),
        #     (30, -95, [0,300], [1,500], [2,12000]),
        #     (31, -95, [0,500], [1,250], [2,900]),
        #     (31, -96, [0,300], [1,700], [2,14000])
        # ]

        c = 2
        while c < len(self.nodes[0]):
            # Create the map plotter:
            # Mark the OMB building as the center of the map, zoom, and plot a range
            omb_loc = (30.61771327808669, -96.33664482193207)
            gmap = gmplot.GoogleMapPlotter(omb_loc[0], omb_loc[1], 10, apikey='')
            gmap.marker(omb_loc[0], omb_loc[1], color='cornflowerblue')
            gmap.circle(omb_loc[0], omb_loc[1], 40000, face_alpha=0)

            for node in self.nodes:
                gmap.marker(node[0], node[1], color='red')
                gmap.circle(node[0], node[1], node[c][2]*1000, face_alpha=0)

            # Draw the map:
            logging.debug("Printing %s", self.nodes[0][c][0])
            gmap.draw(f'./outputs/{self.dataset}/strike_{self.nodes[0][c][1]}.html')
            c += 1

if __name__ == "__main__":
    PostProcess()
