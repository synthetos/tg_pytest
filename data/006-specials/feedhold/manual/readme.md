# Manual Feedhold Tests
This file contains instructions for manual feedhold tests. Generally we use Coolterm version 1.4.3 or earlier for these tests. Other senders may work, but require the following:

* Interactive console to send commands and see results
* Functional XON/XOFF or RTS/CTS flow control
* File send capabilities

### Feedhold Baseline
This test checks if feedholds, resumes and queue flushes are basically working correctly.

**Setup**

1. Position machine so `x100 y77` move will not crash
1. Send `^x` to reset machine

**Test Steps**<br>
Command and _expected result_:

1. Send `g1 f300 x100 y77`
1. Send `!` _HOLD with deceleration_
1. Send `~` _Resume motion_
1. Send `!` _Hold again_
1. Send `?` _Shows X/Y position at hold point_
1. Send `~` _Resume motion_
1. Send `!~` _Move through a rapid hold and resume_
1. Send `!` _Hold again_
1. Send `%` _Flush queue and send STOP status report_
1. Send `g0 x0 y0` _Return to original position_


### Feedhold Multi-Block Test
Tests hold decelerations that span multiple Gcode blocks. XJM and YJM should be set sufficiently low so that a complete deceleration is not possible from 1000 mm/min in 0.5 mm. A jerk value of 100 M is sufficient.

**Setup**

1. Position machine so `x50 y50` move will not crash
1. Send `^x` to reset machine

**Test Steps**<br>
Command and _expected result_:

1. Send file `001-feedhold-multi-line.nc` _Moves about 20mm then stops_


1. Send `!` _HOLD with deceleration_
1. Send `~` _Resume motion_
1. Send `!` _Hold again_
1. Send `?` _Shows X/Y position at hold point_
1. Send `~` _Resume motion_
1. Send `!~` _Move through a rapid hold and resume_
1. Send `!` _Hold again_
1. Send `%` _Flush queue and send STOP status report_
1. Send `g0 x0 y0` _Return to original position_
