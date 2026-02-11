#!/bin/bash
cd /home/harddisk/runningtext/

if ! pgrep -f 'ocr-tv.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/ocr-tv.py & > /home/harddisk/runningtext/ocr-tv.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/ocr-tv.txt
fi
