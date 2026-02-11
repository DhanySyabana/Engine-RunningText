#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'metrotv.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/metrotv.py & > /home/harddisk/runningtext/metrotv.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/metrotv.txt
fi
