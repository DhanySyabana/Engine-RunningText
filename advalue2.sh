#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'advalue2.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/advalue2.py & > /home/harddisk/runningtext/advalue2.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/advalue2.txt
fi
