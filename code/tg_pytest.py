""" pytest.py  Simple functional/regression tester for TinyG and G2

"""
__author__ = 'Alden Hart'
__version__ = '$Revision: 0.1 $'[11:-2]
__date__ = '$Date: 2016/01/14 12:00:00 $'
__copyright__ = 'Copyright (c) 2016 Alden Hart'
__license__ = 'Python'

#### CONSTANTS ####

TEST_DATA_DIR = "../data"
TEST_MASTER_FILE = "test-master.cfg"

OUTFILE_ENABLED = False                 # True or False
SERIAL_TIMEOUT = 1                      # in seconds


#### PACKAGES ####

import sys
import glob
import serial
import json

import os
from os.path import join
from os.path import normpath
from os.path import exists

import time
from time import sleep

from serial.tools.list_ports import comports

# debugging assistants
import inspect
import pprint
from inspect import getmembers


################################################################################
#
#   Serial Ports and Board Initialization
#
#   Return a list of available serial ports or a [None] list
#   Only works on OSX and FTDI (v8)
#   Could be generalized - try something like this (which doesn't work yet):
#    from serial.tools.list_ports import comports
#    uports = sorted(p[0] for p in comports() )
#    ports = [p.encode("utf8") for p in uports]
#
def get_serial_ports():
    return glob.glob('/dev/tty.usb*')

#
#   Open port or die trying
#   Does not yet handle multiple connected devices
#   The test code relies on a reasonable read timeout - like 1 second
#
def open_serial_port(): 
    ports = get_serial_ports()
    if len(ports) == 0:
        print ("No serial port found, Exiting")
        sys.exit(1)
    
    port = ports[0]
    try:
        s = serial.Serial(port, 115200, rtscts=1, timeout=SERIAL_TIMEOUT)
    except:
        print("Could not open serial port %s " % port)
        print("Maybe already open in another program like Coolterm")
        sys.exit(1)
    
    if not s.isOpen :
        print("Could not open serial port: {0}".format(s.name))
        sys.exit(1)
    else:
        print("Serial port opened:    {0}".format(s.name))
    return s

#
#   Initialize TinyG - send something to ensure board is responding and set JSON mode
#
def init_tinyg(s): 
    s.write("{\"fb\":null}\n")      # The first write often returns garbage
    r = s.readline()
    s.write("{\"fb\":null}\n")      # So do it again
    r = s.readline()
    print("Serial port connected: {0}".format(r))


################################################################################
#
#   Test setup 
#
def before_all_tests(s):
    print("SETUP: Before all tests")
    s.write("{clear:null}\n")       # clear any alarms
    responses = s.readlines()       # read all output before returning
    return


def before_each_test_file(s):
#    print("SETUP: Before each test file")
    return


def before_each_test(s):
#    print("SETUP: Before each test")
    return


################################################################################
#
#   Analyzers
#

#
#   analyze_r() - analyze response objects in response list
#
#   t_data is the test specification, which contains analysis data
#   r_datae is a list of decoded JSON responses from the test run
#   out_fd is None if output file is not enabled
#
#   tr_data is the 'r' part of the t_data (derived for convenience)
#   rr_data is the 'r' part of the r_data. Matches to tr_data
#

def analyze_r(t_data, r_datae, out_fd):
    if "r" not in t_data:           # are we analyzing r's in this test?
        return

    tr_data = t_data["r"]
    for r_data in r_datae:
        if "r" not in r_data:       # not an 'r' response line
            continue
            
        rr_data = r_data["r"]       # test if keys are present and match t_data
        for key in tr_data:
            if key in rr_data:
                if tr_data[key] == rr_data[key]:
                    print("  passed: {0}: {1}, {2}".format(key, rr_data[key], r_data["response"]))
                else:
                    print("  FAILED: {0}: {1} should be {2}, {3}".format(key, rr_data[key], tr_data[key], r_data["response"]))
            else:
                print("  MISSING: \"{0}\" is missing from response, {1}".format(key, r_data["response"]))
                
#
#   analyze_sr() - analyze last status report for completion conditions
#
#   t_data is the test specification, which contains analysis data
#   r_data is a list of decoded JSON responses from the test run
#   Currently only checks stat value
#

def analyze_sr(t_data, r_datae, out_fd):
    if "sr" not in t_data:          # are we analyzing sr's in this test?
        return

    # find last SR in the response set
    last_sr = None
    for r_data in r_datae:
        if "sr" in r_data:
            last_sr = r_data
    
    if last_sr == None:
        return

    # test if keys are present and match t_data           
    rsr_data = last_sr["sr"]
    tsr_data = t_data["sr"]

    for key in tsr_data:
        if key in rsr_data:
            if tsr_data[key] == rsr_data[key]:
                print("  passed: {0}: {1}, {2}".format(key, rsr_data[key], last_sr["response"]))
            else:
                print("  FAILED: {0}: {1} should be {2}, {3}".format(key, rsr_data[key], tsr_data[key], last_sr["response"]))
        else:
            print("  MISSING: \"{0}\" is missing from response, {1}".format(key, last_sr["response"]))
        
#
#   analyze_er() - analyze exception reports
#
#   t_data is the test specification, which contains analysis data
#   r_data is a list of decoded JSON responses from the test run
#

def analyze_er(t_data, r_data, out_fd):
    if "er" not in t_data:          # are we analyzing er's in this test?
        return

    for response in r_data:
        if "er" in response:
            print("  EXCEPTION: {0}".format(response["response"]))


################################################################################
#
#   Run a test file with one or more tests
#

def run_test_file(s, t_data, out_fd):
    before_each_test_file(s)

    if "t" not in t_data:
        print("ERROR: No test data provided")
        return
    
    if "label" in t_data["t"]:
        print t_data["t"]["label"]
    
    # Send the test string(s)
    # Can't handle more than 24 lines or 254 chars. Put a sender in or test limits
    send = [x.encode("utf8") for x in t_data["t"]["send"]]   
    for line in send:
        s.write(line+"\n")

    r_datae = []
    for line in s.readlines():
        r_datae.append(json.loads(line))
        r_datae[-1]["response"] = line.strip()   # Add the response line to the dictionary

        if "r" in r_datae[-1]:
            r_datae[-1]["r"]["status"] = r_datae[-1]['f'][1]  # extract status code from footer              
            r_datae[-1]["r"]["count"] = r_datae[-1]['f'][2]   # extract byte/line count from footer
         
    # Run analyzers 
    analyze_r(t_data, r_datae, out_fd)
    analyze_sr(t_data, r_datae, out_fd)
    analyze_er(t_data, r_datae, out_fd)

################################## MAIN PROGRAM BODY ###########################
#
#   Main
#
def main():

    t_data = { "status":0 }

    # Open and initialize TinyG port
    print("Starting TinyG Tester")
    s = open_serial_port()
    init_tinyg(s)               # We are open and ready to rock the kitty time

    # Open master input file - contains a list of JSON files to process
    os.chdir(TEST_DATA_DIR)
    try:
        master_fd = open(TEST_MASTER_FILE, 'r')
    except:
        print("Failed to open test master file {0}".format(TEST_MASTER_FILE))
        s.close()
        sys.exit(1)

    # Build a list of input files and test each one for existence
    print("Adding files to test run")
    temp_files = [x.strip() for x in master_fd.readlines()]     # input list
    test_files = []                                             # processed list

    for file in temp_files:
        if file[:1] == '#':                 # skip over commented lines
            continue

        file = file.split('#')[0].strip()   # strip inline comments from file text line
        try:
            exists(file)
            test_files.append(file)
            print("  FILE: {0}".format(file))
        except:
            print("  FILE: {0} cannot be opened, not added".format(file))
    print    
    
    # Iterate through the master file to run the tests
    timestamp = time.strftime("%Y-%m%d-%H%M", time.localtime()) # e.g. 2016-0111-1414
    before_all_tests(s)
    
    for test_file in test_files:

        # Open input file, read the file and split into 1 or more JSON objects
        in_fd = open(test_file, "r")       
        tests = split_json_file(in_fd)
        if tests == "fail":
            break;

        # Open an output file if enabled
        if OUTFILE_ENABLED:
            out_file = test_file.split('.')[0]   # remove file ext from filename
            out_file = normpath(join(out_file + "-out-" + timestamp + ".txt"))
            try:
                out_fd = open(out_file, 'w')
            except:
                print("Could not open output file {0}".format(out_file))
        else:
            out_fd = None

        # Run the test or tests found in the file
        print
        print("RUNNING: {0}".format(test_file))
        for test in tests:
            status = run_test_file(s, test, out_fd)
            if (status == "quit"):
                break;

    # Close files USB port and exit
    s.close()
    master_fd.close()
    try:
        in_fd.close()
    except:
        pass
    try:  
        out_fd.close()
    except:
        pass
    print
    print("Quit TinyG Tester")


################################## UTILITIES ###################################

#
#   split_json_file
#
#   Accepts a file descriptor for a JSON test file
#   Returns a list of decoded (loaded) JSON objects
#   Test file contains 1 or more independent JSON objects that must be separated 
#     by 1 or more comment lines
#   Comments are any line starting with "#" and must not contain open curlies "{"
#
def split_json_file(fd):
    data = []
    file_text = fd.read()                   # may want a try/except block on this read
    chunks = file_text.split('#')
    chunks = [x.strip() for x in chunks]

    for chunk in chunks:
        if len(chunk) == 0:                 # skip blank line
            continue
        
        if "{" not in chunk:                # skip comment
            continue

        line = chunk[chunk.index("{"):]     # discard leading comment from previous line

        try:
            data.append(json.loads(line))
        except:
            print("{0} FAILED JSON PARSE, QUITTING".format(line))
            return "fail"
            
    return data

#
#  Lame, unfinished attempt to display JSON structs without those annoying 'u' characters all over.
#  Would also like to get rid of the spaces and make it more compact, ideally a single line if not too long
#
# json.dumps(struct, sort_keys=True, indent=4, separators=(',', ': '))
# json.dumps(structure)
# json.dumps(struct, separators=(',',':'))
#    print(json.dumps(r_data, indent=4, separators=(',', ': ')))

def print_dict(dictionary):
    print(utf2str(dictionary))

# http://stackoverflow.com/questions/1254454/fastest-way-to-convert-a-dicts-keys-values-from-unicode-to-str
def utf2str(dictionary):
    """Recursively converts dictionary keys to strings."""
    if not isinstance(dictionary, dict):
        return dictionary
    return dict((str(k), utf2str(v)) 
        for k, v in dictionary.items())


# DO NOT DELETE
if __name__ == "__main__":
    main()
