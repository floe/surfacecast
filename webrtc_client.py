#!/usr/bin/python3

import sys,gi,json,argparse,os
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('Soup', '2.4')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, Soup, GstWebRTC, GstSdp

from gst_helpers import *
from webrtc_peer import WebRTCDecoder
from client import BaseClient

args = None
flags = []

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    logging.info("WebSocket closed by remote.")
    sys.exit(1)

# outgoing Websocket connection
def ws_conn_handler(session, result):
    connection = session.websocket_connect_finish(result)
    wrb = WebRTCDecoder(connection,"client",args.stun,True,flags)
    client = BaseClient("client",wrb)
    connection.connect("closed",ws_close_handler,wrb)

# element message was posted on bus
def message_cb(bus, message):
    name = message.src.name
    struct = message.get_structure()
    # use window-handle message to set title
    if "fps-display" in name and "have-window-handle" in struct.get_name():
        toplevel = message.src.parent.parent.name
        logging.debug("Setting window name for "+toplevel+"...")
        res, val = struct.get_uint64("window-handle")
        # FIXME: this is obviously a hack...
        os.system("xprop -id "+str(val)+" -format _NET_WM_NAME 8u -set _NET_WM_NAME "+toplevel)
    # debug output for automated tests
    if "zbar" in name:
        logging.debug(message.get_structure().to_string())

def on_element_added(thebin, element):

    name = element.get_name()
    if not name.startswith("output_"):
        return

    name = name.split("_")[-1]

    if name == "front" or name == "surface":
        logging.info("Starting video output for "+name)
        videopipe = "videoconvert ! fpsdisplaysink sync=false name={name} text-overlay={args.debug!s}" if args.out == "" else args.out
        add_and_link([ element, Gst.parse_bin_from_description( videopipe.format(name=name,args=args), True ) ])
    elif name == "audio":
        logging.info("Starting audio output")
        add_and_link([ element, new_element("audioconvert"), new_element("autoaudiosink") ])

# "main"
print("\nSurfaceStreams frontend client v0.2.2 - https://github.com/floe/surfacestreams\n")

parser = argparse.ArgumentParser()

parser.add_argument(     "--fake",   help="use fake sources (desc. from -f/-s)",action="store_true")
parser.add_argument("-m","--main",   help="flag this client as main (lowest z)",action="store_true")
parser.add_argument("-o","--own",    help="include own surfacestream in output",action="store_true")
parser.add_argument("-d","--debug",  help="more debug output (-dd=max)",action="count",default=0   )
parser.add_argument("-t","--target", help="server to connect to (%(default)s)", default="127.0.0.1")
parser.add_argument("-a","--audio",  help="audio source (device name or pipeline)",   default=""   )
parser.add_argument("-f","--front",  help="front image source   (device or pipeline)",default=""   )
parser.add_argument("-s","--surface",help="surface image source (device or pipeline)",default=""   )
parser.add_argument("-u","--stun",   help="STUN server", default="stun://stun.l.google.com:19302"  )
parser.add_argument("-p","--port",   help="server HTTPS listening port",  default=8080             )
parser.add_argument("-n","--nick",   help="client nickname", default=""                            )
parser.add_argument(     "--persp",  help="perspective transform", default=""                      )
parser.add_argument(     "--size",   help="surface stream output size", default="1280x720"         )
parser.add_argument(     "--out",    help="video output pipeline", default=""                      )

args = parser.parse_args()
args.size = [ int(n) for n in args.size.split("x") ]
print("Option",args,"\n")

if args.main:
    flags.append({"main":True})
if args.own:
    flags.append({"own":True})
if args.nick != "":
    flags.append({"nick":args.nick})
if args.persp != "":
    flags.append({"perspective":args.persp})

init_pipeline(on_element_added,args.debug)
connect_bus("message::element",message_cb)

if not args.fake and (args.front == "" or args.surface == ""):
    logging.warning("Need to either specify --fake for test sources, or -f/-s for source devices/pipelines.")

add_test_sources(args.front,args.surface,args.audio,args.fake,sw=args.size[0],sh=args.size[1])

session = Soup.Session()
session.set_property("ssl-strict", False)
msg = Soup.Message.new("GET", "wss://"+args.target+":"+str(args.port)+"/ws")
session.websocket_connect_async(msg, None, None, None, ws_conn_handler)

run_mainloop()
