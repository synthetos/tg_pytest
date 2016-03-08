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

def send_stuff_before(key, data):

    if key not in data:  # silent return is OK
        return;

    delay = 0
    if "delay" in data[key]:
        delay = data[key]["delay"]
    
    # Send the setup string(s)
    send = [x.encode("utf8") for x in data[key]["send"]]   
    for line in send:
        print("  before: {0}".format(line))
        tg.write(line+"\n")
        time.sleep(delay)
    
    responses = tg.readlines()       # collect all output before returning
    return

def send_stuff_after(key, data):

    if key not in data:  # silent return is OK
        return;

    delay = 0
    if "delay" in data[key]:
        delay = data[key]["delay"]
    
    # Send the setup string(s)
    send = [x.encode("utf8") for x in data[key]["send"]]   
    for line in send:
        print("  after: {0}".format(line))
        tg.write(line+"\n")
        time.sleep(delay)
    
    responses = tg.readlines()       # collect all output before returning
    return


def before_all_tests(key, data):
    if "label" in data[key]:
        print
        print("BEFORE ALL TESTS: {0}".format(data[key]["label"]))

    tg.write("M2\n")                        # end any motion
    tg.write("{clear:null}\n")              # clear any alarms
    send_stuff_before(key, data)
    return

def after_all_tests(key, data):
    if "label" in data[key]:
        print
        print("AFTER ALL TESTS: {0}".format(data[key]["label"]))

    send_stuff_after(key, data)
    return

def before_each_test(key, data):    # commands are inlined with no label
    send_stuff_before(key, data)
    return
    
def after_each_test(key, data):
    send_stuff_after(key, data)
    return


################################################################################
#
#   Run a test from a file
#

def run_test(t_data, bet_data, aet_data, out_fd):

    if "t" not in t_data:
        print("ERROR: No test data provided")
        return

    if "label" in t_data["t"]:
        print
        print("TEST: {0}".format(t_data["t"]["label"]))

    delay = 0
    if "delay" in t_data["t"]:
        delay = t_data["t"]["delay"]

    # Run 'before_each` strings
    before_each_test("before_each_test", bet_data)

    # Run local 'before' strings
    if "before" in t_data["t"]:
        send = [x.encode("utf8") for x in t_data["t"]["before"]]   
        for line in send:
            print("  before:  {0}".format(line))
            tg.write(line+"\n")
            time.sleep(delay)
        responses = tg.readlines()       # collect all output before returning

    # Send the test string(s)
    # Can't handle more than 24 lines or 254 chars. Put a sender in or test limits
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

    # Run 'after_each' strings
    after_each_test("after_each_test", aet_data)

    # Run local 'after' strings
    if "after" in t_data["t"]:
        send = [x.encode("utf8") for x in t_data["t"]["after"]]   
        for line in send:
            print("  after:  {0}".format(line))
            tg.write(line+"\n")
            time.sleep(delay)
        responses = tg.readlines()       # collect all output before returning
    
    return


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
#    before_all_tests(bat_data)

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
        before_all_data = ""
        before_each_data = ""
        after_all_data = ""
        after_each_data = ""
        
        for obj in tests:

            if "before_all_tests" in obj:
                before_all_data = obj
                continue

            if "before_each_test" in obj:
                before_each_data = obj
                continue

            if "after_all_tests" in obj:
                after_all_data = obj
                continue

            if "after_each_test" in obj:
                after_each_data = obj
                
        # Run tests
        before_all_tests("before_all_tests", before_all_data)
        
        for t_data in tests:
            if "t" in t_data:
                status = run_test(t_data, before_each_data, after_each_data, out_fd)
                if (status == "quit"):
                    break;

        after_all_tests("after_all_tests", after_all_data)

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


################################## UTILITIES ###################################

def split_json_file(fd):
    """
    Accepts a file descriptor for a JSON test file
    Returns a list of decoded (loaded) JSON objects
    Test file contains 1 or more independent JSON objects that must be separated 
      by 1 or more comment lines
    Comments are any line starting with "#" and must not contain open curlies "{"
    """
    try:
        file_text = fd.read()
    except:
        print("Cannot read JSON file")

    chunks = file_text.split('#')
    chunks = [x.strip() for x in chunks]

    data = []
    for chunk in chunks:
        if len(chunk) == 0:                 # skip blank lines
            continue

        if "EOF" in chunk:                  # look for end-of-file marker
            return data

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
