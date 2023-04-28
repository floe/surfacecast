#!/usr/bin/python3
import sys,math

count = 0
avg = 0
avg2 = 0

offset = 10000
if len(sys.argv) > 1:
    offset = sys.argv[1]

#[DEBUG] barcode, timestamp=(guint64)6358626351, stream-time=(guint64)6358626351, running-time=(guint64)6358626351, type=(string)QR-Code, symbol=(string)"\{\"TIMESTAMP\":10604463965\,\"BUFFERCOUNT\":160\,\"FRAMERATE\":\"15/1\"\,\"NAME\":\"DEBUGQROVERLAY0\"\}", quality=(int)1, duration=(guint64)66666666;

for line in sys.stdin:
    
    parts = line.split(",")
    if len(parts) < 6:
        continue
    #print(parts[1],parts[5])

    t_local  = parts[1].split(")")
    t_remote = parts[5].split(":")
    if len(t_local) < 2 or len(t_remote) < 2:
        continue
    #print(t_local,t_remote)

    diff = float(t_remote[1].strip("\\")) - float(t_local[1])
    # convert to ms, with 10 sec offset
    diff = math.fabs(int(offset) - diff/1000000)
    #print(diff)

    count += 1
    avg  += diff
    avg2 += diff*diff

    var = math.fabs(avg2 - (avg*avg)/count)
    print(count, avg/count,math.sqrt(var/count))

    if count >= 1000:
        sys.exit(0)
