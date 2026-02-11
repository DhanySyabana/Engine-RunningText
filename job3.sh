#!/bin/bash
cd /home/harddisk/runningtext/
if ! pgrep -f 'ocr-tv3.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/ocr-tv3.py & > /home/harddisk/runningtext/ocr-tv3.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/ocr-tv3.txt
fi
