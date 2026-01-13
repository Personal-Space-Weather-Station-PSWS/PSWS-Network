# Calculate the latitude of a station from its Maidenhead grid

class CalculateLatitude:
    def calculate_latitude(grid):
#        value_1 = ord(grid[1]) - 65
#        value_1 = value_1 * 10
#        value_2 = int(grid[3])
#        try:
#            value_3 = ord(grid[5]) - 97
#            value_3 = value_3 / 24
#            value_3 = value_3 + (1/48) - 90
#        except Exception:  # in case user supplied only 4 char Maidenhead grid
#            value_3 = 0
        import maidenhead as mh       
        
       # latitude = value_1 + value_2 + value_3
       # return latitude
        return mh.to_location(grid,4)[0]
