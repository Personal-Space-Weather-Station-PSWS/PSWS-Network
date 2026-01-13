# Calculate the longitude of a station from its Maidenhead grid

class CalculateLongitude:
    def calculate_longitude(grid):
#        value_1 = ord(grid[0]) - 65
#        value_1 = value_1 * 20
#        value_2 = int(grid[2]) * 2
#        try:
#            value_3 = ord(grid[4]) - 97
#            value_3 = value_3 / 12
#            value_3 = value_3 + (1/24)
#        except Exception:
#            value_3 = 0
#        longitude = value_1 + value_2 + value_3 - 180
#        return longitude
        import maidenhead as mh

       # latitude = value_1 + value_2 + value_3
       # return latitude

       #  mh.to_location returns an array [lat long]
        return mh.to_location(grid,4)[1]

