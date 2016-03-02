
# tg_pytest

Python-based TinyG tester for v8 and g2 code bases
The tester runs JSON test files and reports results
This project is maintained in the WingIDE Python but can use any Python environment.

Please note: tg_pytest is only intended to get the easy tests done;
It is not intended to be a full-featured test framework. It is not suited
to running continuous tests, i.e. running a Gcode file and looking for the
ongoing results. It's a batch tester, not streaming.

### How It works
 - The tester opens the test-master.cfg file and runs each uncommented JSON file in sequence.
 - Each JSON file contains one or more test structured as a standalone JSON object.
 - Each test is run by sending all the strings in the `send` array, then waiting for all the JSON responses to be returned from the board. Responses may consist of `r`, `sr` and `er` JSON objects. Responses are decoded and put in a list of decoded JSON objects.
 - After a 1 second timeout (settable in python) the tester stops listening and analyzes the response list. A separate analyzer is called for `r`, `sr` and `er` responses. Results are sent to the screen (and in the future to an optional file).
 - Note: `sr` responses are rolled up into a "synthetic" status report, which is the union of all elements received by all status reports. The last instance of an element is what sticks. (It's still useful set status reports to Verbose: See `/data/000-setup/setup-centered-baseline-001.json` for an example.)

### Usage

  - Make sure you have a TinyG v8 or g2 powered and plugged in and it's
      not already connected to some other USB host (like Coolterm)
  - Edit the /data/test-master.cfg file for the tests you want to run
  - Make sure each JSON test file is correct (see below)
  - Run tg_pytest from your Python environment

#### Test Sequence (what should happen):

  - Open a tinyg port or fail trying
  - Open test-master.cfg file
  - Create a test date and time string as an ISO8601 string (future)
  - For each test in the master file:
    - Open the JSON file for that test
    - Create an output file suffixed by the ISO8601 date/time string (future)
    - Iterate through the input file. For each test in the file:
      - Send the test string(s) to the tinyg and collect all responses
      - Parse responses according to test data provided (see below)

### JSON test files:

  - A JSON test file contains one or more tests
    - see `/data/001-smoke/smoke-001.json` for an example
  - Each test is defined by an independent JSON object
  - The JSON objects for the tests must be separated by at least one '#' comment line
  - Adding EOF to a comment line will stop processing at that line

#### Comments:

  - Comments are Python style. Currently only # is supported, not """
  - Open curlies are not allowed in comments '{'
  - Blank lines are also OK, but do not act as test separators

### Tests / Test JSON:

  - A test runs all the `send` lines, collects all the response lines
      (`r`'s, `sr`'s and `er`'s), then analyzes according to the test JSON   
  - Each test must be a parsable JSON object. If in doubt, lint it.
    - It's useful to edit these files in an editor with a built-in
      JSON linter like Atom (use json-linter package).
    - It may also be useful to cut and paste a JSON object into jsonlint.com for checking.

Refer to smoke-001.json to follow along:

  - "t" is the test data object, consisting of:
    - "label" will be displayed when the test is run
    - "send" is na array of one or more strings to send for the test
    - "delay" is optional delay in seconds between sends. Values < 1 are OK
    - "fail" can be "hard" or "soft" (default if omitted). Hard will abort the test run (future)
  - "r" contains the elements to check in all "r" responses:
    - If "r" is present, test all keys for exact match, e.g. xvm:12000
    - Use "status" to match the status in the footer
    - Use "count" to match the count in the footer
  - "sr" contains the elements to check in the status reports:
    - If "sr" is present, test all keys for exact match, e.g. stat:3
  - "er" contains the elements to check in any exception reports
    - Any ERs thrown will be displayed
    - ERs will be displayed by default unless disabled by "display":false
    - No elements are actually matched

As new test functionality is added it will appear here<br>

Note that strings in embedded JSON do not need to be escaped, as TinyG will always accept JSON in relaxed mode, regardless of whether it's set to relaxed or strict JSON mode. (In strict mode all *responses* will be strict, of course). The shortcuts also work, like 't' for true or 'n' for null. The following example still produces valid JSON but is simpler to edit and maintain:

    "t":{"label":"Read axis configuration",
         "send":["{\"x\":null}"],
         "fail":"soft"}         ...can be sent as:

    "t":{"label":"Read axis configuration",
         "send":["{x:n}"],
         "fail":"soft"}

### Running Tests
   - Tests are run in the order listed in `/data/test-master.cfg`
   - Tests can be commented in and out using # in the first char.
   - A test run should start with a setup file such as `/data/000-setup/setup-centered-baseline-001.json`
   - Tests can be designed to run on a naked board (board and motors), or a machine. If the test is run on the machine some guidance should be provided for the initial conditions. It's common to run a test from the middle of travel - i.e. 1/2 way between limits on X, Y and Z. See arc tests for examples.

### Known Limitations and Open Issues:
  - There is no buffer management on the send string, nor is there likely to be. For any given test the send string array should be limited to 254 characters (v8 streaming mode), or 24 lines (v8 line mode), or 3000 characters (g2)  
  - Only exact-match checking is supported. This should be enough for now.

### Changes
- As of 3/1/16 the USB port finder now works on OSX and Windows. It should also work on Linux but has not been tested.

### TODO list
