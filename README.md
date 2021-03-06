# OpenBCI-Brainflow-LSL
---
Uses Python, [BrainFlow](https://github.com/brainflow-dev/brainflow), and [pylsl](https://github.com/labstreaminglayer/liblsl-Python) to read data from Open BCI board and send it as [Lab Streaming Layer (LSL)](https://github.com/sccn/labstreaminglayer) streams.

## Dependencies
Install dependencies in your environment with:

```pip install --upgrade numpy brainflow pylsl pyserial PyYAML``` 

## Usage
Steps:
1. Set up your own settings file. An example of such file is included in this repo as ```settings8.yml```. If you are not going to use Arduino as a source of triggers, just comment out lines 25-33. To see what channel commands (sent to Cyton board) mean, go to [Cyton channels commands](#cyton-channels-commands). A full description can be found in [Open BCI docs](https://docs.openbci.com/docs/02Cyton/CytonSDK). In this examplary file only channels 1-6 are powered up. Default commands are defined as a constant in ```obci_brainflow_lsl.py```
1. Set up your EEG (and Arduino if needed), check signal quality using [OpenBCI GUI](https://docs.openbci.com/docs/06Software/01-OpenBCISoftware/GUIDocs)
1. Run the script with a command including one required argument ```--set``` with the name of a YAML file containing settings: ```python obci_brainflow_lsl.py --set settings8.yml``` and continue with the steps (initiating the session, sending commands, commencing the stream) until the LSL stream is established
1. Record all your LSL streams (continuous data and markers) using e.g. [Lab Recorder](https://github.com/labstreaminglayer/App-LabRecorder) to one *.XDF file
1. View and analyze your data using free software e.g. [EEGLab](https://sccn.ucsd.edu/eeglab/index.php) or [Python MNE library](https://mne.tools/stable/index.html)

My Cyton setup:
|Channel nr|Electrode(s) position|Cyton Board Pin|Board command|
|---|---|---|---|
|1|-VEOG|Bottom N1P|x1040100X|
||+VEOG|Top N1P||
|2|Fz|Bottom N2P|x2060110X|
|3|C3|Bottom N3P|x3060110X|
|4|C4|Bottom N4P|x4060110X|
|5|P3|Bottom N5P|x5060110X|
|6|P4|Bottom N6P|x6060110X|
|7|-|-|x7161000X|
|8|-|-|x8161000X|
|REF|A1|Bottom SRB (SRB2) |-|
|BIAS|AFz|Bottom BIAS |-|


My Arduino circuit:

<img src="https://github.com/marles77/openbci-brainflow-lsl/blob/master/arduino.PNG" width="600">


## Features
The script (written in Python 3.8) enables to stream in parallel several types of data via LSL:

* Open BCI board channels such as EXG/EEG and AUX (accelerometer; if you want to use it, just uncomment line 13 in the settings file)
* Triggers/markers from serial port connected to Arduino board, e.g. photosensors, switch etc. (an example of a simple sketch is included in ```trigger_photo.ino``` file)

## Limitations and known issues
The script has been tested only on Windows with Cyton + Dongle and Cyton + Daisy + Dongle, for now. Any feedback from tests performed on other platforms will be much appreciated.

## Acknowledgments
This program is based on a script originally created by [@retiutut](https://github.com/OpenBCI/OpenBCI_GUI/tree/master/Networking-Test-Kit/LSL). I was also inspired by a similar project [OpenBCI_LSL](https://github.com/openbci-archive/OpenBCI_LSL)

---
### *Cyton channels commands*

||CHANNEL|POWER_DOWN|GAIN_SET|INPUT_TYPE_SET|BIAS_SET|SRB2_SET|SRB1_SET||
|---|---|---|---|---|---|---|---|---|
|x|1-8*|0-1|0-6|0-7|0-1|0-1|0-1|X|
||||0 Gain 1|0 NORMAL|||||
||||1 Gain 2|1 SHORTED|||||
||||2 Gain 4|2 BIAS_MEAS|||||
||||3 Gain 6|3 MVDD|||||
||||4 Gain 8|4 TEMP|||||
||||5 Gain 12|5 TESTSIG|||||
||||6 Gain 24|6 BIAS_DRP|||||
|||||7 BIAS_DRN|||||
|x|1|0|4|0|0|0|0|X|
|x|2|0|6|0|1|1|0|X|
|x|7|1|6|1|0|0|0|X|
---
*channels 9-16 are labeled Q,W,E,R,T,Y,U,I
