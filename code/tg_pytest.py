""" pytest.py  Simple functional/regression tester for TinyG and G2

"""
__author__ = 'Alden Hart'
__version__ = '$Revision: 0.1 $'[11:-2]
__copyright__ = 'Copyright (c) 2016 Alden Hart'
__license__ = 'Python'

#### CONSTANTS ####

TEST_DATA_DIR = "../data"
TEST_MASTER_FILE = "test-master.cfg"
OUTFILE_ENABLED = False     # True or False

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
from tg_utils import TinyG          # Serial ports and board initialization
from tg_utils import split_json_file


################################################################################
#
#   Analyzers
#

def analyze_r(t_data, r_datae, out_fd):
    """
    Analyze response objects in response list
    t_data is the test specification, which contains analysis data
    r_datae is a list of decoded JSON responses from the test run
    out_fd is None if output file is not enabled
    """
    if "r" not in t_data:           # are we analyzing r's in this test?
        return


    for r_data in r_datae:
        if "r" not in r_data:       # this list element is not an 'r' response line
            continue

        if "response" in t_data["r"]:  # suppress the response
            if t_data["r"]["response"] == False:
                r_data["response"] = ""
        """
        for k in t_data["r"]:
            if k in r_data["r"]:
                if t_data["r"][k] == r_data["r"][k]:
                    if display:
                        print("  passed: {0}: {1}, {2}".format(k, r_data["r"][k], r_data["response"]))
                    else:
                        print("  passed: {0}: {1}".format(k, r_data["r"][k]))
                else:
                    if display:
                        print("  FAILED: {0}: {1} should be {2}, {3}".format(k, r_data["r"][k], t_data["r"][k], r_data["response"]))
                    else:
                        print("  FAILED: {0}: {1} should be {2}".format(k, r_data["r"][k], t_data["r"][k]))
        """

        for k in t_data["r"]:
            if k in r_data["r"]:
                if t_data["r"][k] == r_data["r"][k]:
                    print("  passed: {0}: {1} {2}".format(k, r_data["r"][k], r_data["response"]))
                else:
                    print("  FAILED: {0}: {1} should be {2} {3}".format(k, r_data["r"][k], t_data["r"][k], r_data["response"]))
            else:
                print("  MISSING: \"{0}\" is missing from response {1}".format(k, r_data["response"]))


def analyze_sr(t_data, r_datae, out_fd):
    """
    Analyze last status report for completion conditions
    """
    if "sr" not in t_data:          # are we analyzing sr's in this test?
        return

    build_sr = {}                   # build a synthetic SR to reconstruct filtered SRs
    last_sr = None                  # record the last SR
    for r_data in r_datae:
        if "sr" in r_data:
            last_sr = r_data
            for k in r_data["sr"]:  # because a dictionary comprehension won't update KVs in an existing dict?
                build_sr[k] = r_data["sr"][k]

    if last_sr == None:             # return if there were no SRs in the response set
        return

    # test if keys are present and match t_data           
    for k in t_data["sr"]:
        if k in build_sr:
            if t_data["sr"][k] == build_sr[k]:
                print("  passed: {0}: {1}, {2}".format(k, build_sr[k], last_sr["response"]))
            else:
                print("  FAILED: {0}: {1} should be {2}, {3}".format(k, build_sr[k], t_data["sr"][k], last_sr["response"]))
        else:
            print("  MISSING: \"{0}\" is missing from response, {1}".format(k, last_sr["response"]))


def analyze_er(t_data, r_datae, out_fd):
    """
    Analyze exception reports
    Disable using "display":false
    Does not current match any keys - just displays the exception
    """
    if "er" in t_data:
        if "display" in t_data["er"]:
            if t_data["er"]["display"] == False:
                return

    for r_data in r_datae:
        if "er" in r_data:
            print("  EXCEPTION: {0}".format(r_data["response"]))


################################################################################
#
#   Before and afters 
#
#   send_before_after() - inner wrapper that actually sends before/after strings
#   do_before_after()   - outer wrapper for before/after each/all
#

def send_before_after(key, data, delay):
    """
    key == "before" or "after"
    data == flat dictionary containing key (or not)
    """
    if key not in data:             # silent return is OK
        return;

    # Send the before/after strings
    if key == "before" and "before" in data:
        send = [x.encode("utf8") for x in data["before"]]   
        for line in send:
            print("  before: {0}".format(line))
            tg.write(line+"\n")
            time.sleep(delay)

    if key == "after" and "after" in data:
        send = [x.encode("utf8") for x in data["after"]]   
        for line in send:
            print("  after:  {0}".format(line))
            tg.write(line+"\n")
            time.sleep(delay)
    
    responses = tg.readlines()       # collect all output before returning


def do_before_after(key, data):
    """
    key == "before_all", "after_all", "before_each" or "after_each"
    data == dictionary nested under the above key
    """
    
    if key not in data:             # silent return is OK
        return;

    delay = 0                       # extract the 'delay' tag
    if "delay" in data[key]:
        delay = data[key]["delay"]

    if key == "before_each" and "before" in data[key]:
        send_before_after("before", data["before_each"], delay)

    if key == "after_each" and "after" in data[key]:
        send_before_after("after", data["after_each"], delay)
        
    if key == "before_all" and "before" in data[key]:
        if "label" in data[key]:
            print
            print("BEFORE ALL TESTS: {0}".format(data[key]["label"]))

        tg.write("M2\n")            # end any motion and clear any alarms
        tg.write("{clear:null}\n")  # clear any alarms
        send_before_after("before", data["before_all"], delay)
    
    if key == "after_all" and "after" in data[key]:
        if "label" in data[key]:
            print
            print("AFTER ALL TESTS: {0}".format(data[key]["label"]))
            send_before_after("after", data["after_all"], delay)


################################################################################
#
#   Run a test from a file
#

def run_test(t_data, before_data, after_data, out_fd):

    if "t" not in t_data:
        print("ERROR: No test data provided")
        return

    if "label" in t_data["t"]:
        print
        print("TEST: {0}".format(t_data["t"]["label"]))

    delay = 0
    if "delay" in t_data["t"]:
        delay = t_data["t"]["delay"]

    # Run "before" strings
    do_before_after("before_each", before_data)
    send_before_after("before", t_data["t"], delay)       # local before's second

    # Send the test string(s)
    # WARNING: Won't handle more than 24 lines or 254 chars w/o flow control working (RTS/CTS)
    send = [x.encode("utf8") for x in t_data["t"]["send"]]   
    for line in send:
        print("  sending: {0}".format(line))
        tg.write(line+"\n")
        time.sleep(delay)

    r_datae = []
    for line in tg.readlines():
        line = line.strip()
        try:
            r_datae.append(json.loads(line))
        except:
            print("  FAILED: Unable to decode response from TinyG {0}".format(line))
            return

        r_datae[-1]["response"] = line      # Add the response line to the dictionary

        if "r" in r_datae[-1]:
            r_datae[-1]["r"]["status"] = r_datae[-1]['f'][1]  # extract status code from footer              
            r_datae[-1]["r"]["count"] = r_datae[-1]['f'][2]   # extract byte/line count from footer

    # Run analyzers 
    analyze_r(t_data, r_datae, out_fd)
    analyze_sr(t_data, r_datae, out_fd)
    analyze_er(t_data, r_datae, out_fd)

    # Run "after" strings
    send_before_after("after", t_data["t"], delay)      # local after's first
    do_before_after("after_each", after_data)


################################## MAIN PROGRAM BODY ###########################
#
#   Main
#
global tg

tg = TinyG()    # Create the TinyG Object

def main():

    t_data = { "status":0 }
    
    # Open and initialize TinyG port
    print("Starting TinyG Tester")
    tg.init_tinyg()          # Initialize the TinyG connection.
                             # We are open and ready to rock the kitty time

    # Open master input file - contains a list of JSON files to process
    os.chdir(TEST_DATA_DIR)
    try:
        master_fd = open(TEST_MASTER_FILE, 'r')
    except:
        print("Failed to open test master file {0}".format(TEST_MASTER_FILE))
        s.close()
        sys.exit(1)

    # Build a list of input files and test each one for existence
    print("MASTER: Building test set from master file")
    temp_files = [x.strip() for x in master_fd.readlines()]     # raw file list
    test_files = []                                             # processed list

    for file in temp_files:
        if file[:1] == '#':                 # skip over commented lines
            continue

        if file == "":                      # skip over blank lines
            continue

        file = file.split('#')[0].strip()   # strip inline comments from file text line
        try:
            exists(file)
            test_files.append(file)
            print("  {0}".format(file))
        except:
            print("  {0} cannot be opened, not added".format(file))
    print

    # Iterate through the master file list to run the tests
    timestamp = time.strftime("%Y-%m%d-%H%M", time.localtime()) # e.g. 2016-0111-1414

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
        print("FILE: {0}".format(test_file))

        # Extract before/after data objects (it's OK if they don't exist)
        before_all = ""
        before_each = ""
        after_all = ""
        after_each = ""
        
        for obj in tests:

            if "before_all" in obj:
                before_all = obj
                continue

            if "before_each" in obj:
                before_each = obj
                continue

            if "after_all" in obj:
                after_all = obj
                continue

            if "after_each" in obj:
                after_each = obj
                
        # Run tests
        do_before_after("before_all", before_all)
        
        for t_data in tests:
            if "t" in t_data:
                status = run_test(t_data, before_each, after_each, out_fd)
                if (status == "quit"):
                    break;

        do_before_after("after_all", after_all)

    # Close files USB port and exit
    tg.serial_close()
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


# DO NOT DELETE
if __name__ == "__main__":
    main()
