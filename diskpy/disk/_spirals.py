# -*- coding: utf-8 -*-
"""
Implements functions for estimate spiral density wave power in PPDs

Created on Mon Nov  2 13:11:22 2015

@author: ibackus
"""

import pynbody
SimArray = pynbody.array.SimArray
import numpy as np

from diskpy.pdmath import bin2dsum, dA
from diskpy.disk import centerdisk

def spiralpower_t(flist, rbins=50, thetabins=50, binspacing='log', rlim=None, 
                  paramname=None, center=True):
    """
    Estimates the spiral power as a function of r and t for a whole simulation.
    Calculated using spiralpower
    
    Parameters
    ----------
    
    flist : list
        List of SimSnaps or a filelist
    rbins, thetabins : int or arraylike
        Number of bins OR bins to use
    binspacing : str
        'log' or 'linear'.  Spacing of radial bins to use
    rlim : list or array
        If rbins is an int, sets the min and max to consider
    paramname : str
        Optional filename of the param file, used for pynbody.load
    center : bool
        Shift snapshot center of mass to origin and place it in rest frame
    
    Returns
    -------
    
    power : SimArray
        power as a function of t and r.  power[i] gives power vs r at time i
    redges : SimArray
        Radial binedges used
    """
    
    # Check to see if flist is a list of filenames
    do_load = False
    if isinstance(flist[0], str):
        
        do_load = True
    
    # ----------------------------------------------------
    # If radial bins have not been supplied, set them up
    # ----------------------------------------------------
    if isinstance(rbins, int):
        # rbins is the number of bins to use
    
        if rlim is None:
            
            # Limits have not been set
            if do_load:
                f = pynbody.load(flist[0], paramname=paramname)
            else:
                f = flist[0]
            rmin = f.g['rxy'].min()
            rmax = f.g['rxy'].max()
            
        else:
            
            # the limits are set
            rmin = rlim[0]
            rmax = rlim[1]
            
        # Now set up the bins
        if binspacing == 'log':
            
            rbins = np.exp(np.linspace(np.log(rmin), np.log(rmax), rbins+1))
            
        elif binspacing == 'linear':
            
            rbins = np.linspace(rmin, rmax, rbins+1)
            
        else:
            
            raise ValueError, 'Unrecognized binspacing {0}'.format(binspacing)
            
    # ----------------------------------------------------
    # Calculate power vs time
    # ----------------------------------------------------
    power = []
    for i, f in enumerate(flist):
        
        if do_load:
            
            print i
            f = pynbody.load(f, paramname=paramname)
        
        if center:
            
            centerdisk(f)
        p, r = spiralpower(f, rbins, thetabins)
        power.append(p)
        
    # Re-format power as a SimArray (or array if no units)
    if pynbody.units.has_units(power[0]):
        
        units = power[0].units
        power = SimArray(power, units)
        
    else:
        
        power = np.asarray(power)
        
    return power, rbins
    

def spiralpower(f, rbins=50, thetabins=50):
    """
    Estimates the spiral power (non-axisymmetric power) as a function of radius
    Power is calculated as the standard deviation of the surface density 
    along the angular direction.
    
    Parameters
    ----------
    
    f : SimSnap
        Simulation snapshot
    rbins, thetabins : int or arraylike
        Number of bins OR the bins
        
    Returns
    -------
    
    power : SimArray
        Non-axisymmetric power as a function of r
    r : SimArray
        Radial binedges used
    """
    
    rmesh, thetamesh, sigma = sigmacylindrical(f, rbins, thetabins)
    power = np.std(sigma, -1)
    r = rmesh[:,0]
    
    return power, r

def powerspectrum(f, mMax=30, rbins=50):
    """
    The density power spectrum along the angular direction, summed along the
    radial direction.
    
    Parameters
    ----------
    f : SimSnap
        Snapshot of a disk
    mMax : int
        Maximum fourier mode to calculate
    rbins : int or array
        Number of radial bins or the binedges to use
        
    Returns
    -------
    
    m : array
        Array of the fourier modes from 0 to mMax (integers)
    power : array
        Power in the fourier modes, summed along radial direction.  Power is
        take to be the square of the surface density fourier transform
    """
        
    r, m, sigtransform = sigmafft(f, rbins, 2*mMax + 1)
    m = m[0,:]
    power = (abs(sigtransform)**2).sum(0)
    
    return m, power

def sigmafft(f, rbins=50, thetabins=50):
    """
    Calculates the fourier transform of the surface density along the angular
    direction.  Works by binning sigma in r, theta (using sigmacylindrical) and
    doing a fourier transform along the theta axis.
    
    Parameters
    ----------
    f : SimSnap
        Simulation snapshot of a disk
    rbins, thetabins : int or array like
        Number of bins or binedges to use
    
    Returns
    -------
    rmesh : SimArray
        2D Meshgrid of radial binedges
    mmesh : Array
        2D meshgrid of m binedges, where m is an integer (the mth fourier mode)
    sigfft : SimArray
        2D meshgrid of surface density fourier transformed along the angular
        direction.
    
    Notes
    -----
    
    The returned arrays are indexed such that array[i,j] gives the value of
    array at radial bin i and theta bin j.
    """
    
    rmesh, thetamesh, sigma = sigmacylindrical(f, rbins, thetabins)
    sigfft = SimArray(np.fft.rfft(sigma), sigma.units)
    nm = sigfft.shape[1]
    # Normalize sigma
    sigfft /= (nm-1.0)
    # Make r, m meshes
    m = np.arange(0, nm)
    rmesh2, mmesh = np.meshgrid(rmesh[:,0], m)
    
    return rmesh2.T, mmesh.T, sigfft

def sigmacylindrical(f, rbins=50, thetabins=50):
    """
    Estimates the surface density, binned in cylindrical coordinates
    
    Parameters
    ----------
    
    f : SimSnap (see pynbody)
        Snapshot of a disk
    rbins, thetabins : int or arraylike
        Number of bins or binedges.  Theta is calculated between 0 and 2 pi
    
    Returns
    -------
    
    rmesh : SimArray
        2D Meshgrid of radial binedges
    thetamesh : Array
        2D meshgrid of angle binedges
    sigma : SimArray
        2D meshgrid of surface density.
    
    Notes
    -----
    
    The returned arrays are indexed such that array[i,j] gives the value of
    array at radial bin i and theta bin j.
    """
    r = f.g['rxy']
    theta = np.asarray(np.arctan2(f.g['y'], f.g['x']))
    theta = theta % (2*np.pi)
    # Default theta bin edges are 0 to 2 pi, evenly spaced
    if isinstance(thetabins, int):
        
        thetabins = np.linspace(0, 2*np.pi, thetabins + 1)
        
    # Now bin/sum particle masses
    msum, redges, thetaedges = bin2dsum(r, theta, f.g['mass'], rbins, thetabins)
    # sigma = mass/area
    sigma = msum / dA(redges, thetaedges)
    # Do mesh grid
    rmesh, thetamesh = np.meshgrid(redges, thetaedges)
    return rmesh.T, thetamesh.T, sigma
