#!/usr/bin/env python

from setuptools import setup

setup(
    name='SqrMelon',
    version='1.0',
    packages=['.'],
    install_requires=[
        'PyOpenGL==3.1.7',
        'pyprof2calltree==1.4.5',
        'PySide6==6.7.2',
        'PySide6_Addons==6.7.2',
        'PySide6_Essentials==6.7.2',
        'python-osc==1.9.0',
        'Send2Trash==1.8.3',
        'shiboken6==6.7.2',
    ],
    extras_require={
        'numpy': ['numpy'],
    },
    package_dir={'': './'},
    entry_points={
        'console_scripts': [
            'sqrmelon = main:run',
        ],
    },
)
