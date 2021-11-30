#!/usr/bin/python3

import sys,gi,json
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('Soup', '2.4')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, Soup, GstWebRTC, GstSdp

from gst_helpers import *
from client import *
from webrtc_peer import WebRTCPeer

flags = { }

# get address and port from client
def get_client_address(client):
    addr = client.get_remote_address()
    return addr.get_address().to_string()+"_"+str(addr.get_port())

# incoming HTTP(S) request
def http_handler(server,msg,path,query,client,user_data):
    print("HTTP(S) request for "+path)
    flags[get_client_address(client)] = query
    content_type = "text/html"
    try:
        data = open(path[1:],"r").read()
        if path.endswith(".js"):
            content_type = "text/javascript"
    except:
        msg.set_status(Soup.Status.NOT_FOUND)
        return
    msg.response_headers.append("Content-Type",content_type)
    msg.response_headers.append("Cache-Control","no-store")
    msg.response_body.append(data.encode("utf-8"))
    msg.set_status(Soup.Status.OK)

# TODO: add request to restart server
# TODO: add request to flag client as main (lowest z-layer)

# Websocket connection was closed by remote
def ws_close_handler(connection, wrb):
    # TODO actually handle closing (might be tricky, needs to rewire pipeline)
    print("WebSocket closed by remote.")

# incoming Websocket connection
def ws_conn_handler(server, connection, path, client, user_data):

    source = get_client_address(client)
    print("New WebSocket connection from "+source)

    # FIXME: HTTP(S) requests and Websocket connection come from different ports...
    add_new_client(source,{}) # flags[source])
    wrb = WebRTCPeer(connection,source)
    connection.connect("closed",ws_close_handler,wrb)
    # TODO: do we ever need the wrb reference in the Client object?
    #clients[source].wrb = wrb


# "main"
print("SurfaceCast backend mixer v0.1\n")

init_pipeline(on_element_added)

add_test_sources(main=True)

server = Soup.Server()
server.add_handler("/",http_handler,None)
server.add_websocket_handler("/ws",None,None,ws_conn_handler,None)
server.set_ssl_cert_file("cert.pem","key.pem")
server.listen_all(8080,Soup.ServerListenOptions.HTTPS)

run_mainloop()
