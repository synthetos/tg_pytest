
# tg_pytest

Python-based TinyG tester for v8 and g2 code bases.
The tester runs JSON test files and reports results.
This project is maintained in the WingIDE Python but can use any Python environment.

Please note: tg_pytest is only intended to get the easy tests done;
It is not intended to be a full-featured test framework. It is not suited
to running continuous tests, i.e. running a Gcode file and looking for the
ongoing results. It's a batch tester, not streaming.

### How It works
 - The tester opens the test-master.cfg file and runs each uncommented JSON file in sequence.
 - Each JSON file contains one or more tests structured as standalone JSON objects.
 - Each test is run by sending all the strings in the `send` array, then waiting for all the JSON responses to be returned from the board. Responses may consist of `r`, `sr` and `er` JSON objects. Responses are decoded and put in a list of decoded JSON objects.
 - After a 1 second timeout (settable in tg_utils.py) the tester stops listening and analyzes the response list. A separate analyzer is called for `r`, `sr` and `er` responses. Results are sent to the screen (and in the future to an optional file).
 - Note: `sr` responses are rolled up into a "synthetic" status report, which is the union of all elements received by all status reports. The last instance of an element is what sticks (although it's still useful set status reports to verbose).

 - See `/data/000-setup/example-001.json` for examples of items in this readme.

### Usage

  - Make sure you have a TinyG v8 or g2 powered and plugged in and it's
      not already connected to some other USB host (like Coolterm)
  - Edit the /data/test-master.cfg file for the tests you want to run
  - Make sure each JSON test file is correct (see below)
  - Run tg_pytest from your Python environment
  - _Note: The board must be in strict JSON mode or the Python JSON parser will fail_

#### Test Sequence - What should happen when RUN:

  - Opens a tinyg port or fail trying
  - Opens test-master.cfg file
  - Creates a test date and time string as an ISO8601 string (future)
  - For each test in the master file:
    - Opens the JSON file for that test
    - Creates an output file suffixed by the ISO8601 date/time string (future)
    - Iterates through the input file. For each test in file:
      - Send the `before` strings to the board
      - Send the `send` string(s) to the tinyg and collect all responses
      - Analyze responses according to `t` test data provided (see below)
      - send the `after` strings
      - Note that only `send` strings are analyzed. `before` and `after` are not

### JSON test files:
  - A JSON test file contains one or more tests
  - Each test is defined by an independent JSON object
  - JSON objects must be separated by at least one `#` comment line
  - Adding `SKIP` to a comment line will skip the next test
  - Adding `EOF` to a comment line will end the file

#### Comments in JSON test files:
  - Comments start with `#` (Python style). Currently only # is supported, not """
  - Open curlies `{` are not allowed in comments
  - Blank lines are also OK, but do not act as test separators

### Tests / Test JSON:
  - A test `t` runs all the `send` lines, collects all the response lines `r{}`, `sr{}`, `er{}` then analyzes according to the analyzers: JSON tags `r`, `sr`, `er`
  - JSON Elements are listed below, and are not order dependent. Arrays are order dependent.
  - Each JSON test must be a parseable JSON object or the test will fail to execute. If in doubt, lint it.
    - It's useful to edit JSON files in an editor with a built-in JSON linter like Atom (use json-linter package).
    - It can also be useful to paste a JSON object into jsonlint.com for checking
    - JSON syntax errors in either the test JSON or the response JSON (for the board) will cause the test to fail with a message including the offending JSON.  

**JSON Elements** _(See example-001.json for examples)_:
  - `t` is the test data object, consisting of: _(all are optional except `send`)_
    - `label` will be displayed when the test is run
    - `send` array of one or more strings to send for the test (MANDATORY)
    - `delay` delay in seconds between sends. Values < 1.0 are OK
    - `fail` can be `hard` or `soft`. Hard (default) quits the test run if failure
    - `before` array of strings to send before the test - will not be analyzed
    - `after` array of strings to send after the test - will not be analyzed
    - `setup` used to prevent before's and after's from executing in a given test


  - `r` analyzer contains the elements to check in all r{} responses:
    - If `r` is present, test all keys for exact match, e.g. xvm:12000
    - Use `status` to match the status in the footer
    - Use `count` to match the count in the footer (3rd element)
    - Nested keys can also be tested, example:
      - `"send":["{sr:n}"]},` can be tested for:
      - `"r":{"status":0, "sr":{"posx":0.0"}}`


  - `sr` analyzer contains the elements to check in the status reports:
    - If `sr` is present, test all keys for exact match, e.g. `stat:3`


  - `er` analyzer contains the elements to check in any exception reports
    - Any ERs thrown will be displayed
    - ERs will be displayed by default unless disabled by `display:false`
    - No elements are actually matched

Note that strings in embedded JSON do not need to be escaped, as TinyG will always accept JSON in relaxed mode, regardless of whether it's set to relaxed or strict JSON mode. (The board must be in strict mode so all *responses* will be strict, of course). The shortcuts also work, like `t` for `true` or `n` for `null`. The following example still produces valid JSON but is easier to edit and maintain:

    {
      "t":{"label":"Read axis configuration",
         "send":["{\"x\":null}"]}      ...can be sent as:
    }

    {
      "t":{"label":"Read axis configuration",
         "send":["{x:n}"]}
    }

Another trick is to "comment out" a line in a JSON file just invalidate the tag by putting `XXX_` or some other characters (but not #) in front of it. The tag/value will be ignored by the tester.

### Before and After
Additional JSON objects can be provided in a file that will run before and after tests. The JSON format is the same as the `t` object, but only the listed tags are recognized. `before_each` will run prior to local `before`, and `after_each` will run following local `after` in a given test object.

 - `before_all` will run once before all tests in a file:
   - `label` display the label in the output
   - `before` array of strings to send at start of file
   - `delay` optional delay in seconds


 - `after_all` will run once after all tests in a file:
  - `label` display the label in the output
  - `after` array of strings to send after file is complete
  - `delay` optional delay in seconds


 - `before_each` will be run before each test object in a file:
   - `label` is optional, but is not displayed
   - `before` array of strings to send before each test before local `before`
   - `delay` optional delay in seconds


 - `after_each` will be run after each test object in a file:
   - `label` is optional, but is not displayed
   - `after` array of strings to send after each test after local `after`
   - `delay` optional delay in seconds


 - `setup:true`
  - can be included in a test to prevent `before_each`, `after_each` and local `before` and `after` from being run. This supports building setup "tests" that run before the actual tests in the file. _(Note: this tag may evolve to something with more fine-grained control)_

### Defaults
A `defaults` JSON object can be included in a test file. Defaults are read and applied in the location they are found in the file, so it's good to list these first, or sometimes after the before_all. The default settings will be applied to all subsequent tests. Local, per-test settings for the same variables will override the defaults. Values supported include:
- `fail` set as `soft` or `hard`. Hard fail will stop tests immediately on a failure, Defaults to `hard`
- `delay` delay in seconds between sends. Values < 1 are OK
- `display` enable/disable results displays (future)
- `file` enable/disable writing results to files (future)

### Notes on Running Tests
   - Tests are run in the order listed in `/data/test-master.cfg`
   - Tests can be commented in and out using `#` in the first char.
   - A test run should start with a setup file such as `/data/000-setup/setup-centered-001.json`
   - Tests can be designed to run on a naked board (board and motors) or on a machine. If the test is run on the machine some guidance should be provided for the initial conditions. It's common practice to run a test from the middle of travel - i.e. 1/2 way between limits on X, Y and Z. See arc tests for examples.

### Known Limitations and Open Issues:
  - Some limited flow control is provided for TX serial buffer management when transmitting the `before`, `send`, or `after` string arrays. The serial port is set to RTS/CTS, but we have noticed that Pyserial does not reliably use this flow control across all platforms. So it's best if the total byte count of strings sent to the board be limited to 254 characters (v8 streaming mode), or 10 lines (v8 line mode), or 3000 characters (g2). In most tests this should not be an issue.
  - The analyzers only support exact-match checking of results. This should be enough for now.

### Changes
- As of 3/1/16 the USB port finder now works on OSX and Windows. It should also work on Linux but has not been tested.
- Added before, after and SKIP behaviors 3/8/16

### TODO list
