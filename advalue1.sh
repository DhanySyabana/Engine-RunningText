#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'advalue1.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/advalue1.py & > /home/harddisk/runningtext/advalue1.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/advalue1.txt
fi
