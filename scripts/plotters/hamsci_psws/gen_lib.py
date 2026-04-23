import os
import shutil
import collections
import datetime

def get_iterable(x):
    """
    Guarantee that a variable is iterable.

    If x is a single item, return it as a 1-element tuple.
    If x is already iterable, return x.
    """
    if isinstance(x, collections.abc.Iterable) and not isinstance(x,str):
        return x
    else:
        return (x,)

def make_dir(path,clear=False):
    """
    Make a directory. Returns no error if it already exists or the process fails.

    Parameters
    ----------
    path
        path of directory to be created
    clear
        delete any pre-existing directory located at <path>.
    
    """
    if clear:
        try:
            shutil.rmtree(path)
        except:
            pass
    try:
        os.makedirs(path)
    except:
        pass

def adjust_axes(ax_0,ax_1):
    """
    Align the right-hand position of ax_0 to match the right-hand position of ax_1.
    This is useful if ax_1 has a colorbar and ax_0 does not, and you want to make
    sure the x-axes of both ax_objects line up.

    Parameters
    ----------
    ax_0
        matplotlib axis object to be adjusted
    ax_1
        matplotlib axis object that is used as the reference position.
    """
    ax_0_pos    = list(ax_0.get_position().bounds)
    ax_1_pos    = list(ax_1.get_position().bounds)
    ax_0_pos[2] = ax_1_pos[2]
    ax_0.set_position(ax_0_pos)


def datetime2date(dt):
    """
    Return a datetime object stripped of its time information.
    """
    date    = datetime.datetime(dt.year,dt.month,dt.day)
    return date

def decimal_hours(dt):
    """
    Return the decimal hours of a datetime object.
    """
    hours   = dt.hour + dt.minute/60. + dt.second/3600 + (dt.microsecond*1e-6)/3600.
    return hours
