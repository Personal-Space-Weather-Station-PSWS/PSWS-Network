import string
import numpy as np
import pandas as pd

import tqdm

# Create string lookup lists for each of the codes.
alpha_upper = np.char.array([x for x in string.ascii_uppercase])
alpha_lower = np.char.array([x for x in string.ascii_lowercase])
nr_str      = np.char.array(['{!s}'.format(x) for x in range(10)])

def inx_alpha(inx):
    """
    Determine if a string position should be alpha in
    a grid square.
    """

    # Check if the position is odd and decrement if necessary.
    if (inx % 2): inx -= 1

    # Determine if the position should be an alpha char.
    alpha   = not bool((inx/2) % 2)
    return alpha

@np.vectorize
def grid_valid(grid):
    """
    Determine if a gridsquare is valid.
    """
    global pbar
    
    pbar.update(1)
    try:
        gs_len      = len(grid)
    except:
        return False

    # Test length not zero...
    if gs_len == 0:
        return False

    # Make sure an even number
    if gs_len % 2:
        return False

    # Check that alphas and numerics are in the right places.
    for inx,char in enumerate(grid):
        should_be_alpha = inx_alpha(inx)
        valid   = not should_be_alpha ^ char.isalpha()
        if not valid:
            return False

    # If you pass all of the tests, return True!
    return True

def lookup_cty_dat(dct):
    cty = dct['cty']
    row = dct['row']

    dxcc            = cty.getdxcc(row.call_0)
    row['ctry_0']   = dxcc.get('name')
    row['pfx_0']    = dxcc.get('prefix')

    dxcc            = cty.getdxcc(row.call_1)
    row['ctry_1']   = dxcc.get('name')
    row['pfx_1']    = dxcc.get('prefix')

    return row

#def update_df_ctydat(df,ctydat_file):
#    with open(ctydat_file,'r') as cfl:
#        cty             = ctydat.CtyDat(cfl)
#        print('Updating df from ctydat...')
#
#        run_list        = []
#        for inx,row in df.iterrows():
#            run_list.append( {'cty':cty, 'row':row} )
#
#        with mp.Pool() as pool:
#            results = pool.map(lookup_cty_dat,run_list)
#
##        results = []
##        for run_item in run_list:
##            results.append(lookup_cty_dat(run_item))
#
#        df   = pd.DataFrame(results)
#
#    return df

def update_df_ctydat(df,ctydat_file):
    df                  = df.copy()
    CTY_country_0       = []
    CTY_prefix_0        = []
    CTY_country_1       = []
    CTY_prefix_1        = []

    print('Determining DXCC entities...')
    with open(ctydat_file,'r') as cfl:
        cty             = ctydat.CtyDat(cfl)
        print('Updating df from ctydat...')

        for inx,row in tqdm.tqdm(df.iterrows(),total=len(df)):
            dxcc        = cty.getdxcc(row.call_0)
            CTY_country_0.append(dxcc.get('name'))
            CTY_prefix_0.append(dxcc.get('prefix'))

            dxcc        = cty.getdxcc(row.call_1)
            CTY_country_1.append(dxcc.get('name'))
            CTY_prefix_1.append(dxcc.get('prefix'))

    df['ctry_0']  = CTY_country_0
    df['pfx_0']   = CTY_prefix_0
    df['ctry_1']  = CTY_country_1
    df['pfx_1']   = CTY_prefix_1

    return df

def update_df_grid2latlon(df):
    print('Calculating lat/lons...')

    tqdm.tqdm.pandas(tqdm.tqdm,leave=True)
    for key in [0,1]:
        lat_k   = 'lat_{!s}'.format(key)
        lon_k   = 'lon_{!s}'.format(key)
        grid_k  = 'grid_{!s}'.format(key)

        print('{} --> ({}, {})'.format(grid_k,lat_k,lon_k))

        df[lat_k] = np.nan
        df[lon_k] = np.nan

        dft = df.dropna(subset=[grid_k])
        result = dft[grid_k].progress_apply(gs2latlon_cached)

        lats,lons   = zip(*result)

        df.loc[result.index,lat_k] = lats
        df.loc[result.index,lon_k] = lons
    return df

def latlon2gridsquare(lat,lon,precision=6):
    """
    Calculates gridsquares from lat,lon pairs.
    This routine is vectorized.
    
    Precision indicates the desired number of Grid Square characters,
    and must be an even number. 4 is often used in HF communications,
    and 6 is standard for VHF/UHF. Any two locations within the same 
    6-character grid square are no more than 12 km apart.
    """
    #### Make sure input is numpy array with all finite values.
    lats_0  = np.array(lat)
    lons_0  = np.array(lon)

    lats_1  = lats_0.flatten()
    lons_1  = lons_0.flatten()

    lat_lon_good_tf = np.logical_and(np.isfinite(lats_1), np.isfinite(lons_1))

    lats    = lats_1[lat_lon_good_tf]
    lons    = lons_1[lat_lon_good_tf]

    # Make sure all input lons are between -180 and +180 deg.
    tf = lons > 180.
    lons[tf] -= 360.

    # Define zLats that start at 0 at the south pole
    # Define zLons that start at 0 at the antimeridian of Greenwich
    zLats = lats +  90.
    zLons = lons + 180.


    # Calculate the field (a.k.a. first 2 letters)
    base = 18.
    container_size_lat = 180.
    container_size_lon = 360.
    subdivide_size_lat = container_size_lat / base
    subdivide_size_lon = container_size_lon / base

    zLats_rem        = zLats % container_size_lat
    zLons_rem        = zLons % container_size_lon

    lat_code_inx     = np.array(np.floor(zLats_rem / subdivide_size_lat),dtype=np.int)
    lon_code_inx     = np.array(np.floor(zLons_rem / subdivide_size_lon),dtype=np.int)

    lon_code  = alpha_upper[lon_code_inx]
    lat_code  = alpha_upper[lat_code_inx]
    this_code = lon_code + lat_code

    grid_square = this_code
    curr_prec   = 2

    # Square, subsquare, extended square, and beyond...
    while curr_prec < precision:
        # Determine if we use base 10 numerics for base 24 alpha
        # for this portion of the code.
        alpha        = not bool((curr_prec/2) % 2)
        if alpha:
            base     = 24
            str_code = alpha_lower
        else:
            base     = 10.
            str_code = nr_str

        container_size_lat     = subdivide_size_lat
        container_size_lon     = subdivide_size_lon
        subdivide_size_lat     = container_size_lat / base
        subdivide_size_lon     = container_size_lon / base

        zLats_rem        = zLats_rem % container_size_lat
        zLons_rem        = zLons_rem % container_size_lon

        lat_code_inx     = np.array(np.floor(zLats_rem / subdivide_size_lat),dtype=np.int)
        lon_code_inx     = np.array(np.floor(zLons_rem / subdivide_size_lon),dtype=np.int)

        lon_code    = str_code[lon_code_inx]
        lat_code    = str_code[lat_code_inx]
        this_code   = lon_code + lat_code
        grid_square = grid_square + this_code
        curr_prec  += 2

    # Build return array that puts NaNs back in place.
    ret_arr                     = np.zeros([lats_1.size],dtype=grid_square.dtype)
    ret_arr[lat_lon_good_tf]    = grid_square
    ret_arr                     = ret_arr.reshape(lats_0.shape)
        
    return ret_arr

gs_latlon_cache = {}
gs_latlon_cache['center']       = {}
gs_latlon_cache['lower left']   = {}
gs_latlon_cache['upper left']   = {}
gs_latlon_cache['upper right']  = {}
gs_latlon_cache['lower right']  = {}
def gs2latlon_cached(gridsquare,position='center'):
    result  = gs_latlon_cache[position].get(gridsquare)
    if result is None:
        try:
            result  = gridsquare2latlon(gridsquare,position=position)
        except:
            result  = (np.nan,np.nan)
        gs_latlon_cache[position][gridsquare] = result
    return result

def gridsquare2latlon(gridsquare,position='center',new_precision=None):
    """
    Calculates lat,lon pairs from gridsquares.
    This routine is vectorized.

    position options:
        'center'
        'lower left'
        'upper left'
        'upper right'
        'lower right'

    new_precision:
        None: Do not change the precision of the input grid squares.
              If None, all input gridsquares must have the same precision,
              or an exception will be raised.

        Even Integer: Input grid squares will be converted to this new precision.
            Grid squares with less precision will be extended by appending patterns
            of '55' and 'mm' to the correct length.

            Grid squares with greater precision than new_precsion will be truncated.

            Note that this will give a reduction in speed compared to uniform grid
            square precision.
    """    
    global pbar

    # Create string lookup lists for each of the codes.
    alpha_pd = pd.Series(list(range(26)),index=alpha_lower)
    
    # Don't process lines that have no grid square.
    gs_0        = np.array(gridsquare)
    gs_1        = gs_0.flatten()

    with tqdm.tqdm(desc='Checking Grid Square Validity',total=len(gs_1),dynamic_ncols=True) as pbar:
        gs_good_tf  = grid_valid(gs_1)
    gs_2        = gs_1[gs_good_tf]

    # Make sure precision of array is uniform.
    # If it's not uniform, convert all values to the new_precision.
    precs       = np.array([len(x) for x in gs_2])
    precision   = precs.max()

    if new_precision is None:
        new_precision = precision

    elif (np.unique(precs).size != 1) or (precs[0] != new_precision):
        # If a vector of gridsqaures is given without uniform precision,
        # this is a subroutine to pad the gridsquares with less
        # to the center of the cell. e.g. FN20 --> FN20mm
        for gs_inx,gs in tqdm.tqdm(enumerate(gs_2),desc='Adjusting Grid Square Precision',total=len(gs_2),dynamic_ncols=True):
            if len(gs) == new_precision:
                continue
            elif len(gs) > new_precision:
                gs_2[gs_inx] = gs[:new_precision]
            else:
                alpha_next = inx_alpha(len(gs))
                if alpha_next is True:
                    pattern = 'mm55'
                else:
                    pattern = '55mm'

                dpres   = new_precision - len(gs)
                nPatt   = np.ceil(dpres / len(pattern)).astype(np.int)

                gs_2[gs_inx] = (gs + nPatt*pattern)[:new_precision]

            precision = new_precision

    # Make everything lower case and put into a character array
    # for easy slicing.
    gss = [x.lower() for x in gs_2]

    # Seed values for field calculation.
    base               = 18.
    container_size_lat = 180.
    container_size_lon = 360.
    
    # Loop to do actual calculation
    pos, zLat, zLon    = 0,0.,0.
    while pos < precision:
        # Get the 2 characters of the grid square we will work on.
        codes               = [(x[pos],x[pos+1]) for x in gss]
        lon_code, lat_code  = np.array(list(zip(*codes)))

        # Convert code into an index number and choose a base.
        alpha = not bool(pos/2 % 2)
        
        if alpha:
            lon_inx = np.array(alpha_pd.loc[lon_code].tolist(),dtype=np.float)

            lat_inx = np.array(alpha_pd.loc[lat_code].tolist(),dtype=np.float)
            if pos != 0: base = 24.

        else:
            lon_inx = np.array(lon_code,dtype=np.float)
            lat_inx = np.array(lat_code,dtype=np.float)

            base = 10.

        # Determine resolution for this loop.
        subdivide_size_lat = container_size_lat / base
        subdivide_size_lon = container_size_lon / base

        # Add contribution of this loop to zLat and zLon.
        # zLat --> latitude, but south pole is 0 deg
        # zLon --> longitude, but antimeridian of Greenwich is 0 deg
        zLat += (subdivide_size_lat * lat_inx)
        zLon += (subdivide_size_lon * lon_inx)

        # Interate to next to characters in the grid square.
        container_size_lat = subdivide_size_lat
        container_size_lon = subdivide_size_lon
        pos += 2

    # Convert zLat,zLon to lat,lon.
    lat = zLat -  90.
    lon = zLon - 180.

    # Put the lat/lon in the desired location in the cell.
    if position == 'center':
        lat += container_size_lat/2.
        lon += container_size_lon/2.
    elif position == 'lower left':
        # No modification needed for lower left.
        pass
    elif position == 'upper left':
        lat += container_size_lat
    elif position == 'upper right':
        lat += container_size_lat
        lon += container_size_lon
    elif position == 'lower right':
        lon += container_size_lon
    
    # Convert things back to include NaNs.
    ret_lat     = np.ndarray([gs_1.size],dtype=np.float)
    ret_lon     = np.ndarray([gs_1.size],dtype=np.float)

    ret_lat[:]  = np.nan
    ret_lon[:]  = np.nan

    ret_lat[gs_good_tf] = lat
    ret_lon[gs_good_tf] = lon

    ret_lat     = ret_lat.reshape(gs_0.shape)
    ret_lon     = ret_lon.reshape(gs_0.shape)

    return ret_lat,ret_lon

def gridsquare_grid(precision=4):
    """
    Generate a grid of gridsquares up to an arbitrary precision.
    """
    
    # Figure out the size of dLat and dLon for a specified precision.
    N = 1.
    for curr_zPrec in range(int(precision/2)):
        if curr_zPrec == 0:
            # Field case... base 18
            N = N * 18.
        elif curr_zPrec % 2 == 1:
            # Number case... base 10
            N = N * 10.
        else:
            # Alpha case... base 24
            N = N * 24

    dLon = 360./N
    dLat = 180./N

    # Calculate vectors of lats/lons for the desired precsion.
    grid_squares = []
    lons = np.arange(0,360,dLon) - 180. + dLon/2.
    lats = np.arange(0,180,dLat) -  90. + dLat/2.

    # Turn the vectors into a mesh grid and calculate the grid squares.
    lats,lons = np.meshgrid(lats,lons)
    grid_grid = latlon2gridsquare(lats,lons,precision=precision)
    
    return grid_grid

def grid_latlons(precision=4,position='center'):
    """
    Return a grid of gridsquare-based lat/lons.

    precision:
        None:           Use the gridded precsion of this dataset.
        Even integer:   Use specified precision.

    Position Options:
        'center'
        'lower left'
        'upper left'
        'upper right'
        'lower right'
    """
    gs_grid     = gridsquare_grid(precision=precision)
    lat_lons    = gridsquare2latlon(gs_grid,position=position)
    return lat_lons
