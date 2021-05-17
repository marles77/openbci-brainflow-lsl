# obci_brainflow_lsl.py
'''
Author: Marcin Lesniak @marles77 https://github.com/marles77/openbci-brainflow-lsl
Open BCI + BrainFlow + LSL
Use BrainFlow to read data from Open BCI board and send it as LSL streams.
This program is based on a script originally created by Richard Waltman  @retiutut
(OpenBCI): https://github.com/OpenBCI/OpenBCI_GUI/tree/master/Networking-Test-Kit/LSL

Install dependencies with:
pip install --upgrade numpy brainflow pylsl pyserial PyYAML 

This has only been tested with Cyton + Dongle and Cyton + Daisy + Dongle, for now.

Use:
python obci_brainflow_lsl.py --set settings8.yml
'''

import yaml
import sys
import time
import serial
import numpy as np
import threading
import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams
from pylsl import StreamInfo, StreamOutlet, local_clock

# ==== constants ====

CRED = '\033[91m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CEND = '\033[0m'
# default openbci channel commands (to avoid reflushing the board)
OBCI_COMMANDS = ("x1060110X", "x2060110X", "x3060110X", "x4060110X", # channels 1-4   /Cyton
                 "x5060110X", "x6060110X", "x7060110X", "x8060110X", # channels 5-8   /Cyton
                 "xQ060110X", "xW060110X", "xE060110X", "xR060110X", # channels 9-12  /Daisy
                 "xT060110X", "xY060110X", "xU060110X", "xI060110X") # channels 13-16 /Daisy
BOARD_N_CHANNELS = {0: 8, 5: 8, 2: 16, 6: 16} # Cyton or Cyton + Daisy
ALLOWED_DATA_TYPES = ['EXG', 'AUX']
REQUIRED_ARGS = ("board_id", "name", "data_type", "channel_names", "uid", "max_time")
REQUIRED_ARDUINO = ("name", "type", "channel_count", "channel_format", "source_id")
MARKER = {'1': 11, '2': 22} # mapping of external markers; can add more but avoid '0' and '7'

# ==== auxiliary functions ====

def channel_select(board, board_id, data_type): 
    # keys in switcher must correspond to ALLOWED_DATA_TYPES constant
    switcher = { 
        'EXG': board.get_exg_channels(board_id),
        'AUX': board.get_accel_channels(board_id)
    }   
    return switcher.get(data_type, "error")


def read_settings(file_name):
        '''Reads args and board commands from settings file'''

        with open(file_name) as file:
            data = yaml.safe_load(file)

        if data:
            print(CGREEN + "Settings read successfully" + CEND)
            return data
        else:
            print(CRED + "Failed to read settings form file" + CEND)
            return None


def user_choice(prompt, board = None, serial = None, thread_initiated = False):
    '''Awaits user's choice (yes or quit). 
    This function can be used to give the user some control'''
    
    user_res = ''
    while True:#user_res not in ('y', 'q'):
        user_res = input(CYELLOW + prompt + CEND)
        if (user_res == 'y') and (not thread_initiated) and (not stop_event.is_set()):
            break
        if user_res == 'q':
            if thread_initiated:
                stop_event.set() # message for threads to stop
                time.sleep(1)
            if board:
                try:
                    board.stop_stream()
                except brainflow.board_shim.BrainFlowError:
                    print(CRED + "Board is not streaming" + CEND)
                board.release_session()
            if serial:
                serial.write("c".encode()) # message for arduino to stop streaming
                time.sleep(1)
                serial.close()
            print('The end')
            time.sleep(1)
            sys.exit()
        else:
            continue


def default_chan_commands(board_id, chan_commands = None):
    '''Creates a dictionary of default commands for specified board'''

    if not chan_commands:
        n_channels = BOARD_N_CHANNELS[board_id]
        chan_commands = {'chan' + str(num + 1): OBCI_COMMANDS[num] for num in range(0, n_channels)}
        return chan_commands


def manage_settings_data(data):
    '''Reads and manages settings data'''

    args = data.get("args", None)
    arduino = data.get("arduino", None)
    chan_commands = data.get("commands", None)
    if args:
        # manage missing required args
        missing_args = [p for p in REQUIRED_ARGS if args.get(p) == None]
        if missing_args:
            print(CRED + "Missing args:" + CEND, "\n", ", ".join(missing_args), "\nThe end", sep='')
            sys.exit()
        if args['board_id'] not in BOARD_N_CHANNELS:
            print(CRED + "Unsupported board" + CEND, "\nThe end", sep='')
            sys.exit()
        # allowed data types check
        if not all(type in ALLOWED_DATA_TYPES for type in args['data_type']):
            print(CRED + f"Not allowed data type/s in settings. Allowed data types: "
                  + f"{', '.join(ALLOWED_DATA_TYPES)}" + CEND + "\nThe end")
            sys.exit()
        # yaml does not support empty strings, so None values have to be converted
        args['ip_address'] = args['ip_address'] if args.get('ip_address') else ""
        args['streamer_params'] = args['streamer_params'] if args.get('streamer_params') else ""
        args['serial_port'] = args['serial_port'] if args.get('serial_port') else ""
    else:
        print(CRED + "No args" + CEND + "\nThe end")
        sys.exit()
    if arduino:
        # manage missing required args
        missing_arduino = [p for p in REQUIRED_ARDUINO if arduino.get(p) == None]
        if missing_arduino:
            print(CRED + "Missing arduino params:" + CEND, "\n", ", ".join(missing_arduino), "\nThe end", sep='')
            sys.exit()
    else:
        print(CYELLOW + "No arduino params. Continue without external marker stream." + CEND + "\n")

    if not chan_commands:
        # setting default chan commands for Cyton (+ Daisy); alternatively command 'd' can be sent to board
        print(CYELLOW + "No commands. Using default." + CEND, "\nThe end", sep='')
        chan_commands = default_chan_commands(args['board_id'])
    
    return args, arduino, chan_commands


def ping(serial, n = 10):
    '''Estimates mean ping time from n samples (i.e. repeated n times)'''

    list_ping_time = []
    for _ in range(n):
        ser_data = None
        serial.write("x".encode()) # message for arduino to send '7'
        stamp_send = local_clock()
        ser_data = serial.readline().decode('utf-8', errors='ignore').strip()
        if ser_data == "7":
            stamp_received = local_clock()
            list_ping_time.append(stamp_received - stamp_send)
        time.sleep(0.1)
    ping_mean = sum(list_ping_time) / len(list_ping_time)
    print(100 * '-')
    print(f"Mean ping time: {ping_mean}")
    return ping_mean


def collect_markers(serial, outlet, marker_delay):
    '''Collects markers from serial port and sends it via LSL'''

    if serial:
        serial.write("b".encode()) # message for arduino to start reading and sending data
    print(CGREEN + "Now sending data from serial..." + CEND)

    while not stop_event.is_set():
        if (serial.in_waiting):
            stamp = local_clock() - marker_delay
            ser_data = serial.readline().decode('utf-8', errors='ignore').strip().split(',')
            if len(ser_data) > 1:
                marker = MARKER.get(ser_data[0], 0)
                outlet.push_sample(x = [marker], timestamp = stamp)
                #print(f"Marker: {marker} -> time: {stamp}")
                
    #print("Stopped collecting markers")


def collect_cont(board, args, srate, outlet, fw_delay):
    '''Collects continuous data with brainflow and sends it via LSL'''
    
    chans = {}; sent_samples = {}; data = {}; mychunk = {}
    for type in args['data_type']:
        chans[type] = channel_select(board = board, board_id = args['board_id'], data_type = type)
        sent_samples[type] = 0
        
    print(CGREEN + "Now sending data from board..." + CEND)
    start_time = local_clock()

    while not stop_event.is_set():
        # continuous data collection
        elapsed_time = local_clock() - start_time
        data_from_board = board.get_board_data()

        for type in args['data_type']:
            required_samples = int(srate[type] * elapsed_time) - sent_samples[type]
            if required_samples > 0:
                data[type] = data_from_board[chans[type]]
                mychunk[type] = []
                for i in range(len(data[type][0])):
                    mychunk[type].append(data[type][:,i].tolist())
                stamp = local_clock() - fw_delay[type]
                outlet[type].push_chunk(mychunk[type], stamp)
                sent_samples[type] += required_samples
                
        if elapsed_time > args['max_time']:
            stop_event.set() # message for threads to stop
            print(CRED + "\nTime limit reached! Data collection has been stopped." + CEND
                  + CYELLOW + "\nPress 'q' + ENTER to exit\n--> " + CEND, end='')

        time.sleep(1)
        
    #print("Stopped collecting data")


# ==== main function ====

def main(argv):
    '''Takes args and initiates streaming''' 

    if argv:
        # manage settings read form a yaml file
        if argv[0] == '--set':
            file_settings = argv[1]
            data = read_settings(file_settings)
            if not data:
                print('The end')
                sys.exit()
            args, arduino, chan_commands = manage_settings_data(data)
    else:
        print(CRED + "Use --set *.yml to load settings" + CEND, "\nThe end", sep='')
        sys.exit()

    # debug / check data from settings
    #print(f"args:\n{args}\narduino:\n{arduino}\ncommands:\n{chan_commands}\n")

    # open serial port for external triggers (arduino/serial)
    ser = None
    if arduino:
        print("Connecting to serial port...")
        try:
            ser = serial.Serial(arduino["serial_port"], arduino['baud'], write_timeout = 0)
            time.sleep(3) # minimum 2 sec to wake device up!
        except (serial.SerialException, ValueError) as err:
            print(CRED + f"Error: {err}" + CEND)
        if ser:
            ser_data = ser.readline().decode('utf-8', errors='ignore').strip().split(",")
            ser.write("a".encode()) # message for arduino to give "on" sound
            time.sleep(0.5) # must be longer than time of "on" sound from arduino
            print(100 * '-')
            print(CGREEN + f'Established serial connection to Arduino on port: {arduino["serial_port"]} as {arduino["name"]}' + CEND +
                f"\nMessage from board: {ser_data[0]}, reading sensor at {ser_data[1]} Hz")
            ping_time = ping(ser, 10) # estimate mean ping time between pc and arduino

    
    # LSL external outlet (stream form arduino/serial) configuration and initialization
    if ser:
        marker_delay = arduino.get('delay', 0) + ping_time/2 # half the two way transfer time
        info = StreamInfo(name = arduino['name'], type = arduino['type'], 
                        channel_count = arduino['channel_count'],
                        channel_format = arduino['channel_format'], source_id = arduino['source_id'])
        outlet_ext = StreamOutlet(info)
        print(50 * '-')
        print(CGREEN + f'LSL Stream: {info.name()} initialized' + CEND)

    user_choice("Initiate? 'y' -> yes, 'q' -> quit\n--> ", serial = ser)

    BoardShim.enable_dev_board_logger()

    # brainflow initialization
    params = BrainFlowInputParams()
    params.serial_port = args['serial_port']
    params.ip_address = args['ip_address']
    board = BoardShim(args['board_id'], params)
    
    # LSL internal outlet (stream form board) configuration and initialization 
    channel_names = {}; n_channels = {}; srate = {}; info = {}; outlet_int = {}; fw_delay = {}
    for type in args['data_type']:
        channel_names[type] = args['channel_names'][type].split(',')
        n_channels[type] = len(channel_names[type])
        srate[type] = board.get_sampling_rate(args['board_id'])
        name = args['name'] + "_" + type
        uid = args['uid'] + "_" + type
        info[type] = StreamInfo(name, type, n_channels[type], srate[type], 'double64', uid)
        # add channel labels
        chans = info[type].desc().append_child("channels")
        for label in channel_names[type]:
            chan = chans.append_child("channel")
            chan.append_child_value("label", label)
        outlet_int[type] = StreamOutlet(info[type])
        fw_delay[type] = args['delay']

    # prepare session; exit if board is not ready
    try:
        board.prepare_session()
    except brainflow.board_shim.BrainFlowError as e:
        print(CRED + f"Error: {e}" + CEND)
        if ser:
            ser.write("c".encode()) # message for arduino to stop streaming
            time.sleep(1)
            ser.close()
        print("The end")
        time.sleep(1)
        sys.exit()

    # remove daisy if attached, when using only Cyton
    if (args['board_id'] == 0) and (args['daisy_attached']):
        res_query = board.config_board("c")
        time.sleep(0.5)
        print(f"Response to query register settings:\n{res_query}")
    
    # wait until user accepts
    user_choice("Send commands to board? 'y' -> yes, 'q' -> quit\n--> ", board = board, serial = ser)

    # iterate over channel commands, send one and wait for a response from board
    # to restore default channel settings 'd' can be sent
    for chan, command in chan_commands.items():
        res_string = board.config_board(command)
        time.sleep(0.1)
        if res_string.find('Success') != -1:
            res = CGREEN + res_string + CEND
        else:
            res = CRED + res_string + CEND
        print(f"Response from {chan}: {res}")
        
    # show stream configuration and wait until user accepts or quits
    print(50 * "-")
    for type in args['data_type']:
        print(f"{type}:\nNumber of channels: {n_channels[type]}\nSampling rate: {srate[type]}\n"
            f"Time limit: {args['max_time'] // 60} min. {args['max_time'] % 60} sec.\n")
    user_choice("Start streaming? 'y' -> yes, 'q' -> quit\n--> ", board = board, serial = ser)
    
    # board starts streaming
    board.start_stream(45000, args['streamer_params'])
    time.sleep(1)
    
    # define threads which will collect continuous data (e.g. EEG) and markers (if arduino/serial is set up)
    thread_cont = threading.Thread(target = collect_cont, args = [board, args, srate, outlet_int, fw_delay])
    thread_cont.start()
    if ser:
        thread_markers = threading.Thread(target = collect_markers, args = [ser, outlet_ext, marker_delay])
        thread_markers.start()

    # wait for stop message from user while running data collecting threads
    time.sleep(2)
    user_choice("To stop streaming and quit press 'q' + ENTER\n--> ", board = board, serial = ser, thread_initiated = True)


# ==== start the program ====
if __name__ == "__main__":
    stop_event = threading.Event()
    main(sys.argv[1:])