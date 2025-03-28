"""Contains functions for calculating distances between farms.
"""

from math import radians, cos, sin, asin, sqrt


def haversine(lon1: float, lat1: float, lon2: float, lat2: float):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)

    Args:
        lon1  (float): 1st coordinate longitude
        lat1  (float): 1st coordinate latitude
        long2 (float): 2nd coordinate longitude
        lat2  (float): 2nd coordinate latitude

    Returns:
        distance (in kilometer) between the two points
    """

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.

    return c * r
