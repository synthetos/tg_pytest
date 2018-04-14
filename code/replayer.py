import time
import serial
import json
import argparse
from threading import Timer, Thread, RLock


class G2FlightReplayer(object):
    def __init__(self, control_path, data_path=None):
        self.control_path = control_path
        self.data_path = data_path
        self.control_port = self.data_port = None
        self.lock = RLock()
        self.done = False

    def open(self):
        self.control_port = serial.Serial(self.control_path, 115200, timeout=0, rtscts=True)
        if(self.data_path):
            self.data_port = serial.Serial(self.data_path, 115200, timeout=1)
        def read():
            line = []
            while not self.done:
                self.lock.acquire()
                count = self.control_port.in_waiting
                if count:
                    s = self.control_port.read(count)
                    self.lock.release()
                    for ch in s:
                        line.append(ch)
                        if(ch == '\n'):
                            print '<---------------- %s' % repr(''.join(line))[1:-1]
                            line = []
                else:
                    self.lock.release()
            self.close()
        t = Thread(target=read)
        t.start()

    def close(self):
        for port in (self.control_port, self.data_port):
            if port: port.close()

    def play(self,recording):
        records = recording['records']
        self.pc = 0
        start_time = time.time()

        def next_record():
            current_time = (time.time() - start_time)*1000.0
            
            if self.pc >= len(records):
                self.done = True
                return

            record = records[self.pc]

            if record['dir'] == 'out':
                record_time = record['t']
                if record_time <= current_time:
                    print "--- %08d ---> %s" % (record['t'], repr(record['data'])[2:-1])
                    b = record['data'].encode('latin-1')
                    self.lock.acquire()
                    self.control_port.write(b)
                    self.lock.release()
                    self.pc += 1
                    next_record()
                else:
                    time_to_wait = max(record_time - current_time, 0)
                    t = Timer(time_to_wait/1000.0, next_record)
                    t.start()
            else:
                self.pc += 1
                next_record()

        self.open()
        next_record()


def load_flight_recording(filename):
    with open(filename) as fp:
        flight_recording = json.load(fp)
    return flight_recording


def main(args):
    recording = load_flight_recording(args.filename)
    if(args.show):
        for record in recording['records']:
            if record['dir'] == 'out':
                print record['data'].replace('\n', '\\n')
    else:
        player = G2FlightReplayer(args.control, args.data)
        player.play(recording)

def parse_args():
    parser = argparse.ArgumentParser(description='Play a G2 Flight Recording')
    parser.add_argument('--control', help='Path to the control port')
    parser.add_argument('--data', help='Path to the data port')
    parser.add_argument('--show', action='store_const', const=True, help='Show a printout of all the messages sent')
    parser.add_argument('filename', help='Replay JSON file')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    main(args)