#!/usr/bin/env bash

# A simple file to make default being to plot PV, but not removing the easy file viewing functionality.
# this was made because at the core I want it to still be identical to silx viewer in the sense that
# you can simply call 'pv-visualizer <filename>' and open the file, but I know beamline personnel
# will want to plot pvs as default. At least as a quick fix, I didnt wat this to be implemented in the
# main python code at least until I think about how to do this in a more elegant way.

APPLICATION_DIR=/usr/local/scripts/gui/pv-silx-viewer/pv_silx_viewer/

if [ -z "${@}" ]; then

    micromamba run -p /opt/micromamba/envs/visualizer \
    $APPLICATION_DIR/visualizer.py -p SIM:image1: --pv

else

    micromamba run -p /opt/micromamba/envs/visualizer \
    $APPLICATION_DIR/visualizer.py ${@}

fi
