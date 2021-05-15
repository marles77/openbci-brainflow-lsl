# openbci-brainflow-lsl
Use [BrainFlow library](https://github.com/brainflow-dev/brainflow) to read data from Open BCI board and send it as [ab Streaming Layer (LSL)](https://github.com/sccn/labstreaminglayer) streams.

Dependencies
Install dependencies with:

```pip install --upgrade numpy brainflow pylsl pyserial PyYAML``` 

## Usage
Steps:
1. Set up your own settings file. An example of such file is included in this repo as ```settings8.yml```. If you are not going to use Arduino as a source of triggers, just comment out lines 25-33. To learn about channel commands which are sent to Cyton board read [Open BCI docs](https://docs.openbci.com/docs/02Cyton/CytonSDK). In this examplary file only channels 1-5 are powered up. Default commands are defined as a constant in ```obci_brainflow_lsl.py```
1. Run the script with a command including one required argument ```--set``` with the name of a YAML file containing settings: ```python obci_brainflow_lsl.py --set settings8.yml```
1. Record all your LSL streams using e.g. [Lab Recorder](https://github.com/labstreaminglayer/App-LabRecorder) to one *.XDF file
1. View and analyze your data using free software e.g. [EEGLab](https://sccn.ucsd.edu/eeglab/index.php) or [Python MNE library](https://mne.tools/stable/index.html)

My Arduino circuit:
<img src="https://github.com/marles77/openbci-brainflow-lsl/blob/master/arduino_photo.PNG" width="400">


## Features
The script (written in Python 3.8) enables to stream in parallel several types of data via LSL:

* Open BCI board channels such as EXG/EEG and AUX (accelerometer; if you want to use it, just uncomment line 13 in the settings file)
* Triggers/markers from serial port connected to Arduino board, e.g. photosensors, switch etc. (an example of a simple sketch is included in ```trigger_photo.ino``` file)

##Limitations
The script has been tested only on Windows with with Cyton + Dongle and Cyton + Daisy + Dongle, for now.

## Acknowledgments
This program is based on a script originally created by [@retiutut](https://github.com/OpenBCI/OpenBCI_GUI/tree/master/Networking-Test-Kit/LSL). I was also inspired by a similar project [OpenBCI_LSL](https://github.com/openbci-archive/OpenBCI_LSL)
