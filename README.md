# EduDownloader
A simple script for downloading slides and exercises for university lectures.

Currently the script is usable for websites without login, TU Darmstadt's moodles and faculty sites.

## Requirements
EduDownloader has been written to run with Python 3.5.x and above.

## Installation
Run `pip install -r requirements.txt` in EduDownloaders's root directory to install all necessary
third-party requirements.

## Configuration
The configuration is located at `data/config.yaml`. A sample one is provided in the `data` folder.
Copy it, rename it to `config.yaml` and adjust your settings.

## Extension
You can create new classes which inherit from `Source` in the plugins directory and use them in your
configuration.
