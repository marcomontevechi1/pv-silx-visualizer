#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='pv-silx-viewer',
    version='0.1.0',
    description='Silx-based PV and hdf5 file visualizer',
    url='https://gitlab.cnpem.br/SOL/GUI/pv-silx-viewer',
    author='Marco A. B. Montevechi',
    packages=find_packages(exclude=("images",)),
    install_requires=['numpy>=1.25',
                      'matplotlib',
                      'scikit-image',
                      'sharedarray',
                      'scipy==1.11',
                      'pkgconfig==1.5',
                      'silx==1.1',
                      'h5py==3.9.0',
                      'pyepics',
                      'pyyaml',
                      ],
)
