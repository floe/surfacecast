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

pipeline = None

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    # TODO actually handle closing (might be tricky, needs to rewire pipeline)
    print("WebSocket closed by remote.")

# outgoing Websocket connection
def ws_conn_handler(session, result):
    connection = session.websocket_connect_finish(result)
    wrb = WebRTCPeer(connection,"client",is_client=True)
    connection.connect("closed",ws_close_handler,wrb)

# "main"
init_pipeline()

add_and_link([
    new_element("videotestsrc",{"is-live":True,"pattern":"smpte"}),
    new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=640,height=360,framerate=15/1")}),
    new_element("tee",{"allow-not-linked":True},"testsource")
])

add_and_link([
    new_element("audiotestsrc",{"is-live":True,"wave":"ticks"}),
    new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=U8,rate=8000,channels=1")}),
    new_element("tee",{"allow-not-linked":True},"audiotest")
])

session = Soup.Session()
session.set_property("ssl-strict", False)
msg = Soup.Message.new("GET", "wss://127.0.0.1:8080/ws")
session.websocket_connect_async(msg, None, None, None, ws_conn_handler)
#msg = Soup.Message.new("GET", "https://127.0.0.1:8080/stream.html")
#session.add_feature(Soup.Logger.new(Soup.LoggerLogLevel.BODY, -1))
#session.queue_message(msg,ws_conn_handler,None)

run_mainloop()

