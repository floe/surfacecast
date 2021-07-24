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

clients = {}

class Client:

    def __init__(self):

        self.wrb = None
        self.inputs  = {}
        self.outputs = {}


# incoming HTTP(S) request
def http_handler(server,msg,path,query,client,user_data):
    content_type = "text/html"
    try:
        data = open(path[1:],"r").read()
        if path.endswith(".js"):
            content_type = "text/javascript"
    except:
        msg.set_status(Soup.Status.NOT_FOUND)
        return
    msg.response_headers.append("Content-Type",content_type)
    msg.response_body.append(data.encode("utf-8"))
    msg.set_status(Soup.Status.OK)

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    # TODO actually handle closing (might be tricky, needs to rewire pipeline)
    print("WebSocket closed by remote.")

# incoming Websocket connection
def ws_conn_handler(server, connection, path, client, user_data):

    addr = client.get_remote_address()
    source = addr.get_address().to_string()+"_"+str(addr.get_port())
    print("New WebSocket connection from "+source)

    clients[source] = Client()
    wrb = WebRTCPeer(connection,source)
    connection.connect("closed",ws_close_handler,wrb)
    clients[source].wrb = wrb

def on_element_added(thebin, element):

    elname = element.get_name().split("_")
    if len(elname) != 4:
        return

    direction = elname[0]
    source = elname[1]+"_"+elname[2]
    stype = elname[3]
    #print(direction,source,stype)

    if direction == "output":
        clients[source].outputs[stype] = element
    if direction == "input":
        clients[source].inputs[stype] = element

    # are all outputs in place?
    if len(clients[source].outputs) == 3:
        print("Client elements complete.")

# "main"
init_pipeline(on_element_added)

add_test_sources()

server = Soup.Server()
server.add_handler("/",http_handler,None)
server.add_websocket_handler("/ws",None,None,ws_conn_handler,None)
server.set_ssl_cert_file("cert.pem","key.pem")
server.listen_all(8080,Soup.ServerListenOptions.HTTPS)

run_mainloop()
