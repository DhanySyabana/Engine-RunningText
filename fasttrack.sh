#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'fasttrack.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/fasttrack.py > /home/harddisk/runningtext/fasttrack.out 2>&1 &
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/fasttrack.txt
fi
