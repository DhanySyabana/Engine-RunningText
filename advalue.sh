#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'advalue.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/advalue.py & > /home/harddisk/runningtext/advalue.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/advalue.txt
fi
