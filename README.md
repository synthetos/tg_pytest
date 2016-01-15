
# tg_pytest

Python-based TinyG tester for v8 and g2 code bases
The tester runs JSON test files and reports results
This project is maintained in the WingIDE Python but can use any Python environment.

Please note: tg_pytest is only intended to get the easy tests done;
It is not intended to be a full-featured test framework. It is not suited
to running continuous tests, i.e. running a Gcode file and looking for the
ongoing results. It's a batch tester, not streaming.

### Usage:

  - Make sure you have a TinyG v8 or g2 powered and plugged in and it's
      not already connected to some other USB host (like Coolterm)
  - Edit the /data/test-master.cfg file for the tests tou want to run
  - Make sure each JSON test file is correct (see below)
  - Run tg_pytest from your Python environment

#### Test Sequence (what should happen):

  - Open a tinyg port or fail trying
  - Open test-master.cfg file
  - Create a test date and time string as an ISO8601 string
  - For each test in the master file:
    - Open the JSON file for that test
    - Create an output file suffixed by the ISO8601 date/time string
    - Iterate through the input file. For each test in the file:
      - Send the test string(s) to the tinyg and collect all responses
      - Parse responses according to test data provided (see below)

### JSON test files:

  - A JSON test file contains one or more tests (see test-001.json)
  - Each test is defined by an independent JSON object
  - Tests must be separated by at least one '#' comment line

#### Comments:

  - Comments are Python style. Currently only # is supported, not """
  - Open curlies are not allowed in comments '{'
  - Blank lines are OK, but are not test separators

### Tests / Test JSON:

  - A test runs all the send lines, collects all the response lines
      (r's, sr's and er's), then analyzes according to the test JSON   
  - Each test must be a parsable JSON object. If in doubt, lint it
      It's useful to edit these files in an editor with a built-in
      JSON linter like Atom (use json-linter package)
  - Not much is supported yet. As new items are added they will appear here

Refer to test-001.json to follow along:

  - "t" is the test data object, consisting of:
    - "label" will be displayed when the test is run
    - "send" is na array of one or more strings to send for the test
    - "delay" is an optional delay in seconds between send lines. Values < 1 are OK
    - "fail" can be "hard" or "soft" (default if omitted). Hard will abort the test run (not yet implemented)
  - "r" contains the elements to check in all "r" responses:
    - If "r" is present, test all keys for exact match, e.g. xvm:12000
    - Use "status" to match the status in the footer
    - Use "count" to match the count in the footer
  - "sr" contains the elements to check in the status reports:
    - If "sr" is present, test all keys or exact match, e.g. stat:3
  - "er" contains the elements to check in any exception reports
    - Any ERs thrown will be displayed
    - ERs will be displayed by default unless disabled by "display":false
    - No elements are actually matched

Note that strings in embedded JSON do not need to be escaped, as TinyG will always accept JSON in relaxed mode, regardless of whether it's set to relaxed or strict JSON mode. (In strict mode all *responses* will be strict, of course). The shortcuts also work, like 't' for true or 'n' for null. The following example still produces valid JSON but is simpler to edit and maintain:

    "t":{"label":"Read axis configuration",
         "send":["{\"x\":null}"],
         "fail":"soft"}         ...can be sent as:

    "t":{"label":"Read axis configuration",
         "send":["{x:n}"],
         "fail":"soft"}

### Known Limitations and Open Issues:
  - Currently the USB port finder only works on OSX, but can be relatively easily extended to Linux and Windows as all it needs to do is find the USB port string
  - There is no buffer management on the send string, nor is there likely to be. For any given test the send string array should be limited to 254 characters (v8 streaming mode), or 24 lines (v8 line mode), or 3000 characters (g2)  
  - Only exact-match checking is supported. This should be enough

### TODO list
