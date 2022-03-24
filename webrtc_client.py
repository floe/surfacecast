#!/usr/bin/python3

import sys,gi,json,argparse,os
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('Soup', '2.4')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, Soup, GstWebRTC, GstSdp

from gst_helpers import *
from webrtc_peer import WebRTCPeer
from client import BaseClient

args = None
sink = ""

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    logging.info("WebSocket closed by remote.")
    sys.exit(1)

# outgoing Websocket connection
def ws_conn_handler(session, result):
    connection = session.websocket_connect_finish(result)
    wrb = WebRTCPeer(connection,"client",args.stun,is_client=True,is_main=args.main)
    client = BaseClient("client",wrb)
    connection.connect("closed",ws_close_handler,wrb)

# element message was posted on bus
def message_cb(bus, message):
    struct = message.get_structure()
    res, val = struct.get_uint64("window-handle")
    if res:
        # FIXME: this is obviously a hack...
        os.system("xprop -id "+str(val)+" -format _NET_WM_NAME 8u -set _NET_WM_NAME "+sink)

def on_element_added(thebin, element):

    global sink

    name = element.get_name()
    if not name.startswith("output_"):
        return

    name = name.split("_")[-1]

    if name == "front" or name == "surface":
        logging.info("Starting video output for "+name)
        add_and_link([ element, new_element("videoconvert"), new_element("fpsdisplaysink", {"text-overlay":args.debug}) ])
        sink = name
    elif name == "audio":
        logging.info("Starting audio output")
        add_and_link([ element, new_element("audioconvert"), new_element("autoaudiosink") ])

# "main"
print("\nSurfaceStreams frontend client v0.1.0 - https://github.com/floe/surfacestreams\n")

parser = argparse.ArgumentParser()

parser.add_argument(     "--fake",   help="use fake sources (desc. from -f/-s)",action="store_true")
parser.add_argument("-m","--main",   help="flag this client as main (lowest z)",action="store_true")
parser.add_argument("-d","--debug",  help="more debug output (-dd=max)",action="count",default=0   )
parser.add_argument("-t","--target", help="server to connect to (%(default)s)", default="127.0.0.1")
parser.add_argument("-a","--audio",  help="audio source (device name or pipeline)",   default=""   )
parser.add_argument("-f","--front",  help="front image source   (device or pipeline)",default=""   )
parser.add_argument("-s","--surface",help="surface image source (device or pipeline)",default=""   )
parser.add_argument("-u","--stun",   help="STUN server", default="stun://stun.l.google.com:19302"  )
parser.add_argument("-p","--port",   help="server HTTPS listening port",  default=8080             )

args = parser.parse_args()
print("Option",args,"\n")

init_pipeline(on_element_added,args.debug)
connect_bus("message::element",message_cb)

if not args.fake and (args.front == "" or args.surface == ""):
    logging.warning("Need to either specify --fake for test sources, or -f/-s for source devices/pipelines.")

add_test_sources(args.front,args.surface,args.audio,args.fake)

session = Soup.Session()
session.set_property("ssl-strict", False)
msg = Soup.Message.new("GET", "wss://"+args.target+":"+args.port+"/ws")
session.websocket_connect_async(msg, None, None, None, ws_conn_handler)

run_mainloop()
