## /004-specials/planner/

This directory contains a series of planner stress tests.
These tests are best run with firmware compiled at DEBUG=2 and connected to a hardware debugger. Many of the failed tests generate traps that you will want to examine with the debugger.

These tests check:
- Certain motion planner conditions that have failed in the past (planner cases)
- Boundary cases that can fire planner and related traps and other error conditions
