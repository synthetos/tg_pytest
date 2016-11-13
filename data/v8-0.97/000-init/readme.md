## Common initializations

This directory contains initializations for various test scenarios<br>
These can be included in test files by inserting then in an include line.<br>
The leading # must be present and be on the first character.<br>
The inits are numbered in the order they should be applied. 01 should (almost) always be run.

For example:
```
# include 000-init/init-01-defaults-001.json
# include 000-init/init-02-json-g2-0.99-001.json
# include 000-init/init-03-gcode-001.json
```
