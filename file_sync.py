# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uControl, uLoggerLevel

from c_file_sync import *

import sys,os

config_file = "sync-files.ini"
if len(sys.argv)>1:
    config_file = sys.argv[1]
if os.path.isfile(config_file) is False:
    print(f'Configuration file not found: {config_file}')
    exit (-1)

uControl.PrintFailures()
control = uControl("FileSync", config_file) # use this line if a custom uControl is not desired
control.GetLogger().SetWriteLevel(Level=uLoggerLevel.DETAILS)
control.GetLogger().SetPrint(Print=True, Level=uLoggerLevel.DETAILS, Color=True)
control.Execute ()

# Note the following about error messages.  There are three categories of error messages:
# - System level uControl messages
# - System level uConfig messages
# - User level command messages

# The SetPrint() method enables printing of the log to the console based on the specified logging level
# The PrintFailures() method turns on console printing of uControl and uConfig failures
# This will result in uControl and uConfig failures displaying twice in the console, but only once in the log
