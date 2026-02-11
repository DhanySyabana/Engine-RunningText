#!/bin/bash
cd /home/harddisk/runningtext/
if ! pgrep -f 'ocr-tv4.py'
then
    nohup /home/harddisk/runningtext/bin/python /home/harddisk/runningtext/ocr-tv4.py & > /home/harddisk/runningtext/ocr-tv4.out
# run the test, remove the two lines below afterwards
else
    echo "running" > ~/ocr-tv4.txt
fi
