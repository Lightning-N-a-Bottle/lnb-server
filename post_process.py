""" post_process.py

    Handle all processing of the acquired data here

    Notes:
        - https://stackoverflow.com/questions/54120759/gmplot-api-issue
        - https://pypi.org/project/gmplot/
        - https://github.com/gmplot/gmplot/wiki
"""

import gmplot
gmap = gmplot.GoogleMapPlotter

gmap.apikey = "inserting my API key here"

latitude_list = [ 30.3358376, 30.307977, 30.3216419 ]

longitude_list = [ 77.8701919, 78.048457, 78.0413095 ]

gmap = gmplot.GoogleMapPlotter(30.3184945,
                            78.03219179999999, 13)

gmap.scatter( latitude_list, longitude_list, '# FF0000',
                            size = 40, marker = False)

gmap.polygon(latitude_list, longitude_list,
               color = 'cornflowerblue')

gmap.draw("path to save .html")