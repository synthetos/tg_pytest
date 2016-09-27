""" pytest.py  Simple functional/regression tester for TinyG and G2

"""
__author__ = 'Alden Hart'
__version__ = '$Revision: 0.2 $'[11:-2]
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

import types

from serial.tools.list_ports import comports

# debugging assistants
import inspect
import pprint
from inspect import getmembers
from tg_utils import TinyG          # Serial ports and board initialization
from tg_utils import split_json_file


################################################################################
#
#   Helpers
#

def fail_hard(t_data, params, line):
    fail = "hard"                       # default to hard fail
    if "fail" in t_data["t"]:           # local fail setting takes precedence over
        fail = t_data["t"]["fail"]
    elif "fail" in params:              # ...default setting
        fail = params["fail"]
    if fail == "hard":
        print("FAIL HARD: Exiting immediately: {0}".format(line))
        sys.exit(1)
    return


def compare_r(key, test_val, resp_val, response_string, params):
    precision = params["use_precision"]
    test = False

    if test_val == "*":                 # Pass all wildcards
        test = True
    
    elif test_val == None:              # Null values are not valid for numerical tests that follow
        if resp_val == None:
            test = True

    else:                               # Test a numeric value against precision
        if abs(test_val - resp_val) <= precision:
            test = True

    if test == True:
        print("  passed: {0}: {1} {2}".format(key, test_val, response_string))
        return (0)
    
    else:
        print("  FAILED: {0}: {1} should be {2} {3}".format(key, resp_val, test_val, response_string))
        return (1)
        

################################################################################
#
#   Analyzers
#
    
def analyze_r(t_data, r_datae, params):
    """
    Analyze response objects in response list
    t_data is the test specification, which contains analysis data
    r_datae is a list of decoded JSON responses from the test run
    params contains output and display instructions and handles
    return 0 if all tests passed, a negative number if failed
    """
    if "r" not in t_data:           # are we analyzing r's in this test?
        return 0

    result = 0
    for r_data in r_datae:
        if "r" not in r_data:       # this list element is not an 'r' response line
            continue

        if "response" in t_data["r"]:  # suppress the response
            if t_data["r"]["response"] == False:
                r_data["response"] = ""
                
        for key in t_data["r"]:
            if key in r_data["r"]:

                test_val = t_data["r"][key]    # data value to check from test data
                resp_val = r_data["r"][key]    # data value returned for this key from response
                
                # compare and display nested responses
                if isinstance(test_val, dict):
                    for child in test_val:
                        if child in resp_val:
                            child_display = key + ":{ " + child
                            result -= compare_r(child_display, test_val[child], resp_val[child], "}", params)
                        else:
                            print("  MISSING: \"{0}\" is missing from response".format(child))
                            result -= 1
                    continue
                
                # compare and display non-nested responses
                result -= compare_r(key, test_val, resp_val, r_data["response"], params)
            else:
                print("  MISSING: \"{0}\" is missing from response {1}".format(key, r_data["response"]))
                result -= 1
                
    return result


def analyze_sr(t_data, r_datae, params):
    """
    Analyze last status report for completion conditions
    """
    if "sr" not in t_data:          # are we analyzing sr's in this test?
        return 0

    result = 0
    build_sr = {}                   # build a synthetic SR to reconstruct filtered SRs
    last_sr = None                  # record the last SR
    for r_data in r_datae:
        if "sr" in r_data:
            last_sr = r_data
            for k in r_data["sr"]:  # because a dictionary comprehension won't update KVs in an existing dict?
                build_sr[k] = r_data["sr"][k]

    if last_sr == None:             # return if there were no SRs in the response set
        return 0

    print last_sr["response"]       # print response just once for all SR tests

    # test if keys are present and match t_data           
    for k in t_data["sr"]:
        if k in build_sr:
            if t_data["sr"][k] == build_sr[k]:
                print("  passed: {0}: {1}".format(k, build_sr[k]))
            else:
                print("  FAILED: {0}: {1} should be {2}".format(k, build_sr[k], t_data["sr"][k]))
                result -= 1
        else:
            print("  MISSING: \"{0}\" is missing from response".format(k))

    return result


def analyze_er(t_data, r_datae, params):
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

    return 0


################################################################################
#
#   Before and After
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


def do_before_after(key, data, params):
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

def run_test(t_data, before_data, after_data, params):

    if "t" not in t_data:
        print("ERROR: No test data provided")
        return

    if "label" in t_data["t"]:
        print
        print("TEST: {0}".format(t_data["t"]["label"]))

    # Get a delay time from params or a local override
    delay = 0
    if "delay" in t_data["t"]:          # local setting takes precedence
        delay = t_data["t"]["delay"]
    elif "delay" in params:             #...default setting
        delay = params["delay"]

    # Get a precision for comparisons from params or a local override
    # If a local precision was provided use the local
    # If a default was provided but no local, use the default
    # If neither default nor local were provided use 0 (exact match)

    if "precision" in t_data["t"]:      # local setting takes precedence
        params["use_precision"] = t_data["t"]["precision"]
    elif "precision" in params:
        params["use_precision"] = params["precision"]
    else:
        params["use_precision"] = 0

    # Check if this is a setup "test"
    setup = False
    if "setup" in t_data["t"]:
        setup = True

    # Run "before" strings if this is not a setup "test"
    if not setup:
        do_before_after("before_each", before_data, params)
        send_before_after("before", t_data["t"], delay)       # local before's second

    # Send the test string(s)
    # WARNING: Won't handle more than 24 lines or 254 chars w/o flow control working (RTS/CTS)
    if "send" not in t_data["t"]:
        print("!!! TEST HAS NO SEND DATA: {0}".format(t_data["t"]["label"]))
        return
    
    send = [x.encode("utf8") for x in t_data["t"]["send"]]
    first_line = send[0]                # used later in no-response cases    
    for line in send:
        print("  sending: {0}".format(line))
        tg.write(line+"\n")
        time.sleep(delay)

    # Collect the response objects
    r_datae = []
    for line in tg.readlines():
        line = line.strip()
        try:
            r_datae.append(json.loads(line))
        except:
            print("  FAILED: Response doesn't parse: {0}".format(line))
            fail_hard(t_data, params, line)
            return

        r_datae[-1]["response"] = line      # Add the response line to the dictionary

        if "r" in r_datae[-1]:
            r_datae[-1]["r"]["status"] = r_datae[-1]['f'][1]  # extract status code from footer              
            r_datae[-1]["r"]["count"] = r_datae[-1]['f'][2]   # extract byte/line count from footer

    if len(r_datae) == 0:
        print ("  FAILED: No response from board: {0}".format(first_line))
        fail_hard(t_data, params, line)

    # Run analyzers on the response object list
    results = 0
    results += analyze_r(t_data, r_datae, params)
    results += analyze_sr(t_data, r_datae, params)
    results += analyze_er(t_data, r_datae, params)

    if results < 0:
        fail_hard(t_data, params, line)

    # Run "after" strings if this is not a setup "test"
    if not setup:
        send_before_after("after", t_data["t"], delay)      # local after's first
        do_before_after("after_each", after_data, params)


################################## MAIN PROGRAM BODY ###########################
#
#   Main
#
global tg

tg = TinyG()    # Create the TinyG Object

def main():

    # Open and initialize TinyG port
    tg.init_tinyg()          # Initialize the TinyG connection
                             # We are open and ready to rock the kitty time

    # Open master input file - contains a list of JSON files to process
    os.chdir(TEST_DATA_DIR)
    try:
        master_fd = open(TEST_MASTER_FILE, 'r')
    except:
        print("Failed to open test master FILE: {0}".format(TEST_MASTER_FILE))
        s.close()
        sys.exit(1)

    # Build a list of input files and test each one for existence
    print("Building test set from FILE: {0}".format(TEST_MASTER_FILE))
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
        except:
            print("  {0} cannot be opened, not added".format(file))

    # Iterate through the master file list to run the tests
    timestamp = time.strftime("%Y-%m%d-%H%M", time.localtime()) # e.g. 2016-0111-1414

    t_data = { "status":0 }

    for test_file in test_files:
        
        # Display filename so opening or parsing errors are obvious
        print
        print("===========================================================")
        
        # Open input file, read the file and split into 1 or more JSON objects
        try:
            in_fd = open(test_file, 'r')
        except:
            print("CANNOT OPEN: {0}".format(test_file))
            exit(1)
            
        print("RUN: {0}".format(test_file))
        tests = []
        tests = split_json_file(in_fd, tests, "  ")
        if tests == None:
            break;

        # Extract defaults and before/after data objects (it's OK if they don't exist)
        before_all = ""
        before_each = ""
        after_all = ""
        after_each = ""
        params = ""
        
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
                
            if "defaults" in obj:
                params = obj["defaults"]
            else:
                params = {}     # create an empty dictionary if defaults doesn't exist

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
        do_before_after("before_all", before_all, params)
        
        for t_data in tests:
            if "t" in t_data:
                status = run_test(t_data, before_each, after_each, params)
                if (status == "quit"):
                    break;

        do_before_after("after_all", after_all, params)

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
    print("TESTS COMPLETE")
    print("Quit TinyG Tester")
    print('\a')

# DO NOT DELETE
if __name__ == "__main__":
    main()
