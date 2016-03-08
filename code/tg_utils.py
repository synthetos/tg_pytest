#!/usr/bin/env python

"""
Utility class to clean up the logic for alden :)

"""
import sys, serial, glob
import json


class TinyG(object):

    def __init__(self):
        self.SERIAL_TIMEOUT = 1          # in seconds
        self.s = self.open_serial_port()
        print("Opened the port")
        
    def write(self, data):
        self.s.write(data)
        
    def serial_close(self):
        self.s.close()
    
    def readlines(self):
        return self.s.readlines();
        
    def init_tinyg(self):
        """
        Initialize TinyG - send something to ensure board is responding and set JSON mode
        """
        self.write("{\"fb\":null}\n")      # The first write often returns garbage
        r = self.s.readline()
        self.write("{\"fb\":null}\n")      # So do it again
        r = self.s.readline()
        self.write("{\"sr\":null}\n")      # So do it again
        r = self.s.readline()
        print("Serial port connected: {0}".format(r))    
        

    def open_serial_port(self): 
        """
        Open port or die trying
        Does not yet handle multiple connected devices
        """
        ports =self.get_serial_ports()
        if len(ports) == 0:
            print ("No serial port found, Exiting")
            sys.exit(1)
    
        port = ports[0]
        
        for port in ports:
            if port.find("Bluetooth") == -1: #We are excluding the built in bluetooth ports on osx here
                try:
                    s = serial.Serial(port, 115200, rtscts=1, timeout=self.SERIAL_TIMEOUT)
                except:
                    print("Could not open serial port %s " % port)
                    print("Maybe already open in another program like Coolterm")
                    print("Quit TinyG Tester")
                    sys.exit(1)
            
                if not s.isOpen :
                    print("Could not open serial port: {0}".format(s.name))
                    sys.exit(1)
                else:
                    print("Serial port opened:    {0}".format(s.name))
                return s    
    
    def get_serial_ports(self):
        """ Lists serial port names
    
            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
    
        result = []
        for port in ports:
           
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result
    
    

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

    skip = False
    
    chunks = file_text.split('#')
    chunks = [x.strip() for x in chunks]

    data = []
    for chunk in chunks:
        if len(chunk) == 0:                 # skip blank lines
            continue

        if "EOF" in chunk:                  # look for end-of-file marker
            return data

        if "SKIP" in chunk:                 # look to skip the next object
            skip = True

        if "{" not in chunk:                # skip comment
            continue

        line = chunk[chunk.index("{"):]     # discard leading comment from previous line

        if not skip:
            try:
                data.append(json.loads(line))
            except:
                print("{0} FAILED JSON PARSE, QUITTING".format(line))
                return "fail"
        else:
            skip = False

    return data
