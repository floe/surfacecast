#!/usr/bin/python3

import sys,gi,json
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('Soup', '2.4')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, Soup, GstWebRTC, GstSdp

from gst_helpers import *
from webrtc_peer import WebRTCPeer

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    print("WebSocket closed by remote.")
    sys.exit(1)

# outgoing Websocket connection
def ws_conn_handler(session, result):
    connection = session.websocket_connect_finish(result)
    wrb = WebRTCPeer(connection,"client",is_client=True)
    connection.connect("closed",ws_close_handler,wrb)

def on_element_added(thebin, element):

    name = element.get_name()
    if not name.startswith("output_"):
        return

    name = name.split("_")[-1]

    if name == "front" or name == "surface":
        add_and_link([ element, new_element("videoconvert"), new_element("fpsdisplaysink",{"sync":False}) ])
    elif name == "audio":
        add_and_link([ element, new_element("audioconvert"), new_element("autoaudiosink",{"sync":False}) ])


# "main"
print("SurfaceCast frontend client v0.1\n")

init_pipeline(on_element_added)

# TODO: use non-fake sources (ideally configurable)
add_test_sources(frontdev="/dev/video0",surfdev="/dev/video10")

target = "127.0.0.1" if len(sys.argv) < 2 else sys.argv[1]

session = Soup.Session()
session.set_property("ssl-strict", False)
msg = Soup.Message.new("GET", "wss://"+target+":8080/ws")
session.websocket_connect_async(msg, None, None, None, ws_conn_handler)
#msg = Soup.Message.new("GET", "https://127.0.0.1:8080/stream.html")
#session.add_feature(Soup.Logger.new(Soup.LoggerLogLevel.BODY, -1))
#session.queue_message(msg,ws_conn_handler,None)

run_mainloop()

