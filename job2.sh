#!/bin/bash
cd /home/harddisk/runningtext/
if ! pgrep -f 'ocr-tv2.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/ocr-tv2.py & > /home/harddisk/runningtext/ocr-tv2.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/ocr-tv2.txt
fi
