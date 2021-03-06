# -*- coding: utf-8 -*-
"""
This is the global settings module for diskpy.  To access the global settings,
simply import them:

    from diskpy import global_settings

Changing/accessing settings is the same as for a dict, ie:
    global_settings[key] = val
    
Settings can be saved via global_settings.save()

Defaults can be restored by global_settings.restore_defaults()


Created on Mon Aug 11 14:38:17 2014

@author: ibackus
"""

import cPickle as pickle
import os
import socket
from textwrap import TextWrapper
import diskpy

_dir = os.path.dirname(os.path.abspath(__file__))
_filename = os.path.join(_dir, 'global_settings.p')

# --------------------------------------------------------------
# DEFAULT SETTINGS
# --------------------------------------------------------------
defaults = {}

# ***** Misc *****
misc = {}
# Maximum number of particles used in calculating velocities
misc['max_particles'] = int(1e7)
defaults['misc'] = misc

# ***** Cluster presets *****
node_info = {}
node_info['scheduler'] = 'PBS'
defaults['node_info'] = node_info

# ***** ChaNGa presets *****

# Format : [runner, runner args, ChaNGa, ChaNGa args]
"""
changa_presets = {}
changa_presets['local'] = ['charmrun_sinks', '++local', 'ChaNGa_sinks', '-D 3 +consph']
changa_presets['mpi'] = ['mpirun', '--mca mtl mx --mca pml cm', 'ChaNGa_uw_mpi', '-D 3 +consph']
changa_presets['default'] = 'local'
defaults['changa_presets'] = changa_presets
"""
#dflemin3 edited 06/10/2015 to run on my computer
#dflemin3 removed _sinks, added +p4 to changa_presets
changa_presets = {}
changa_presets['local'] = ['charmrun', '+p4 ++local', 'ChaNGa', '-D 3 +consph']
changa_presets['mpi'] = ['mpirun', '--mca mtl mx --mca pml cm', 'ChaNGa_uw_mpi', '-D 3 +consph']
changa_presets['default'] = 'local'
defaults['changa_presets'] = changa_presets


# Glass file for ICgen
glassfile = 'glass16.std'
defaults['misc']['icgen-glass-file'] = glassfile

# --------------------------------------------------------------
# Settings class
# --------------------------------------------------------------

def recursive_update(old, new):
    """
    Basically do dict update, but if the value is a dict, recursively apply
    this update to that.
    
    Update old with the values in new
    """
    for k, v in new.iteritems():
        
        if isinstance(v, dict) and isinstance(old.get(k, None), dict):
            recursive_update(old[k], v)
        else:
            old[k] = v

class settings(dict):
    """
    Global settings object.  Call without arguments to echo settings.
    
    Changing/accessing settings is the same as for a dict, ie:
        global_settings[key] = val
        
    Settings can be saved via global_settings.save()
    
    Defaults can be restored by global_settings.restore_defaults()
    
    Dynamically generated settings (such as node information) can be
    re-generated by global_settings.dynamic_settings().
    """
    @classmethod
    def loader(cls, filename):
        
        return pickle.load(open(filename, 'rb'))
        
    def __init__(self):
        
        dict.__init__(self)
        self.filename = _filename
        
        # Load settings and compare to defaults. If the settings don't contain
        # an entry in defaults, add it to the settings
        current_settings = defaults
        
        if os.path.isfile(self.filename):
            
            # Load up previous settings
            saved_settings = settings.loader(self.filename)
            recursive_update(current_settings, saved_settings)
            
        for key, val in current_settings.iteritems():
            
            self[key] = val
            
        self.dynamic_settings()
        
    def __call__(self):
        
        def print_dict(a, n_tabs = 0):
            
            tab = n_tabs * 2 * ' '
            
            wrapper = TextWrapper(80, tab, tab)
            
            for key, val in a.iteritems():
                
                if isinstance(val, dict):
                    
                    print ''
                    print wrapper.fill('{0}'.format(key))
                    #print n_tabs*'  ', key, ':'
                    print_dict(val, n_tabs+1)
                    print ''
                    
                else:
                    
                    #print n_tabs*'  ',key,val
                    print wrapper.fill('{0} : {1}'.format(key,val))
                    
        print '**** GLOBAL SETTINGS ****'
        print_dict(self)
            
    def restore_defaults(self):
        """
        Restore to default settings
        """
        keys = self.keys()
        
        for key in keys:
            
            self.pop(key, None)
            
        for key, val in defaults.iteritems():
            
            self[key] = val
            
        self.dynamic_settings()
            
    def dynamic_settings(self):
        """
        Generates the dynamically created settings
        """
        # --------------------------------------------------------
        # Generate node information
        # --------------------------------------------------------
        node_info = self['node_info']
        node_info['hostname'] = socket.gethostname()
        scheduler = node_info['scheduler']
            
        if scheduler == 'PBS':
            
            if 'PBS_NODEFILE' not in os.environ:
                
                nodelist = [node_info['hostname']]
                
            else:
                
                nodefile = os.environ['PBS_NODEFILE']
                nodelist = []
                
                for line in open(nodefile,'r'):
                    
                    nodelist.append(line.strip())
                    
                nodelist = list(set(nodelist))
            
        else:
            # Assume there's no scheduler
            return [node_info['hostname']]
        
        node_info['nodelist'] = nodelist
        secondary_nodes = set(node_info['nodelist'])
        secondary_nodes.discard(node_info['hostname'])
        node_info['secondary_nodes'] = list(secondary_nodes)
        self['node_info'] = node_info
        
        # Dynamically generated changa presets
        
        if 'mpi' in self['changa_presets']:
            
            mpi_largefiles = list(self['changa_presets']['mpi'])
            hosts = ','.join(node_info['secondary_nodes'])
            host_flag = ' --host ' + hosts
            mpi_largefiles[1] += host_flag
            self['changa_presets']['mpi_largefiles'] = mpi_largefiles
            
        # Diskpy file-names etc...
        diskpy_dir = os.path.realpath(os.path.dirname(diskpy.__file__))
        bin_dir = os.path.join(os.path.dirname(diskpy_dir), 'bin')
        self['misc']['diskpy-dir'] = diskpy_dir
        self['misc']['bin-dir'] = bin_dir

        
    def save(self):
        """
        Save settings
        """
        
        pickle.dump(self, open(self.filename, 'wb'), 2)
        
# --------------------------------------------------------------
# Create settings
# --------------------------------------------------------------

global_settings = settings()