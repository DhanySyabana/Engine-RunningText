#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'deletor.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/deletor.py & > /home/harddisk/runningtext/deletor.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/deletor.txt
fi
