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

frontmixer  = None
frontstream = None

# position offsets for 4 front streams
# FIXME: how to handle > 4 clients?
offsets = [
    (640,360),
    (  0,  0),
    (640,  0),
    (  0,360)
]

class Client:

    def __init__(self,name):

        self.wrb = None
        self.name = name
        self.inputs  = {}
        self.outputs = {}
        self.mixers = {}

    def create_mixers(self):

        if "audio" in self.mixers or "surface" in self.mixers:
            return

        # setup surface & audio mixer
        print("    creating mixers for client "+self.name)
        self.mixers["surface"] = new_element("compositor",{"background":"black"},myname="mixer_"+self.name)
        self.mixers["audio"]   = new_element("audiomixer",myname="audio_"+self.name)
        add_and_link([self.mixers["surface"]])
        add_and_link([self.mixers["audio"]])

    # link client to frontmixer
    def link_to_front(self):

        # FIXME: frontstream is separately encoded for each client ATM, should be one single encoder
        if not "front" in self.inputs or not "front" in self.outputs:
            return

        print("    linking client "+self.name+" to frontmixer")

        # link frontstream tee to client-specific muxer
        link_to_inputselector(frontstream,"src_%u",self.inputs["front"])

        # request and link pads from tee and frontmixer
        sinkpad = link_request_pads(self.outputs["front"],"src_%u",frontmixer,"sink_%u")
        #sinkpad.set_property("max-last-buffer-repeat",10000000000) # apparently not needed

        # set xpos/ypos properties on pad according to sequence number
        # FIXME: only works with <= 4 clients at the moment
        padnum = int(sinkpad.get_name().split("_")[1])
        sinkpad.set_property("xpos",offsets[padnum][0])
        sinkpad.set_property("ypos",offsets[padnum][1])

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

    clients[source] = Client(source)
    wrb = WebRTCPeer(connection,source)
    connection.connect("closed",ws_close_handler,wrb)
    clients[source].wrb = wrb

# create single mixer for front stream
def create_frontmixer_queue():

    global frontmixer
    global frontstream

    if frontmixer != None or frontstream != None:
        return

    print("  creating frontmixer subqueue")

    frontmixer  = new_element("compositor",myname="frontmixer")
    frontstream = new_element("tee",{"allow-not-linked":True},myname="frontstream")

    add_and_link([
        frontmixer,
        #new_element("videoconvert"),
        # TODO: capsfilter here, probably
        #new_element("queue",{"max-size-buffers":1}),
        #new_element("x264enc",x264params),
        frontstream
    ])

# link new client to mixers
def link_new_client(client):

    create_frontmixer_queue()

    print("  setting up mixers for new client "+client.name)

    # create surface/audio mixers for _all_ clients that don't have one yet
    # needs to loop through all clients for the case where 2 or more clients
    # appear simultaneously, otherwise there are no mixers to link to
    #for c in clients:
    #    clients[c].create_mixers()

    # add missing frontmixer links
    client.link_to_front()

    # add missing surface/audio mixer links
    #client.link_all_streams(clients)

# new top-level element added to pipeline
def on_element_added(thebin, element):

    # check format: {input,output}_IPADDR_PORT_{surface,front,audio}
    elname = element.get_name().split("_")
    if len(elname) != 4:
        return

    direction = elname[0]
    source = elname[1]+"_"+elname[2]
    stype = elname[3]
    #print(direction,source,stype)

    client = clients[source]

    if direction == "output":
        client.outputs[stype] = element
    if direction == "input":
        client.inputs[stype] = element

    # are all outputs in place?
    if len(client.outputs) == 3:
        print("Client elements complete.")
        link_new_client(client)

# "main"
init_pipeline(on_element_added)

add_test_sources()

server = Soup.Server()
server.add_handler("/",http_handler,None)
server.add_websocket_handler("/ws",None,None,ws_conn_handler,None)
server.set_ssl_cert_file("cert.pem","key.pem")
server.listen_all(8080,Soup.ServerListenOptions.HTTPS)

run_mainloop()
