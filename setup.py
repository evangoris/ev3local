import os
from setuptools import setup

config = {
    "name": "ev3local",
    "version": "0.0.0",
    "author": "Evan Goris",
    "author_email": "evangoris@gmail.com",
    "description": "Some code to run on the ev3: interface to hardware, pid control, webservices",
    "packages": ["ev3local"],
    "scripts": ["samples/cdetect.py"],
    "install_requires": ["evdev"]
    }

setup(**config)
