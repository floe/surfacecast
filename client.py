#!/usr/bin/python3

import sys,gi,json
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('Soup', '2.4')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, Soup, GstWebRTC, GstSdp

from gst_helpers import *

# client object pool
clients = {}

frontmixer  = None
frontstream = None

# links between individual client tee/mixer pairs
mixer_links = []

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
        self.flags = {}
        self.inputs  = {}
        self.outputs = {}
        self.mixers = {}
        clients[name] = self

    def process(self, msg):
        self.flags[msg] = True
        print("Setting flags for",self.name,":",self.flags)

    # create mixer & converter
    def create_mixer(self,mtype,mixer,convert,caps):

        if mtype in self.mixers:
            return

        print("    creating "+mtype+" mixer for client "+self.name)
        self.mixers[mtype] = mixer
        add_and_link([mixer,convert,caps])
        link_to_inputselector(caps,"src",self.inputs[mtype])

    # link client to frontmixer
    def link_to_front(self):

        # FIXME: frontstream is separately encoded for each client ATM, should be one single encoder
        if not "front" in self.inputs or not "front" in self.outputs:
            return

        print("    linking client "+self.name+" to frontmixer")

        # link frontstream tee to client-specific muxer
        # TODO: seems to work witouth queue?
        link_to_inputselector(frontstream,"src_%u",self.inputs["front"])

        # request and link pads from tee and frontmixer
        # TODO: needs a queue or not?
        sinkpad = link_request_pads(self.outputs["front"],"src_%u",frontmixer,"sink_%u")

        # set xpos/ypos properties on pad according to sequence number
        # FIXME: only works with <= 4 clients at the moment
        padnum = int(sinkpad.get_name().split("_")[1])
        sinkpad.set_property("xpos",offsets[padnum][0])
        sinkpad.set_property("ypos",offsets[padnum][1])

    # helper function to link source tees to destination mixers
    def link_streams_oneway(self,dest,prefix,qparams):

        linkname = prefix+"_"+self.name+"_"+dest.name
        if not linkname in mixer_links:

            print("    linking client "+self.name+" to "+prefix+"mixer "+dest.name)
            # TODO: needs a queue?
            sinkpad = link_request_pads(self.outputs[prefix],"src_%u",dest.mixers[prefix],"sink_%u")
            mixer_links.append(linkname)

            # for the "main" surface, destination mixer pad needs zorder = 0
            if prefix == "surface" and "main" in self.flags:
                print("    fixing zorder for main client")
                sinkpad.set_property("zorder",0)

    # link all other clients to this mixer, this client to other mixers
    def link_streams(self,clients,prefix,qparams):

        for c in clients:

            if c == self.name: # skip own ssrc
                continue

            other = clients[c]

            # for every _other_ mixer, link my tee to that mixer
            self.link_streams_oneway(other,prefix,qparams)

            # for every _other_ tee, link that tee to my mixer
            other.link_streams_oneway(self,prefix,qparams)

    # link all other clients to local mixer, this client to other mixers
    def link_all_streams(self,clients):
        self.link_streams(clients,"surface",{"max-size-buffers":1})
        self.link_streams(clients,"audio",{"max-size-time":100000000})


# create single mixer for front stream
def create_frontmixer_queue():

    global frontmixer
    global frontstream

    if frontmixer != None or frontstream != None:
        return

    print("  creating frontmixer subqueue")

    frontmixer  = new_element("compositor",myname="frontmixer")
    frontstream = new_element("tee",{"allow-not-linked":True},myname="frontstream")

    add_and_link([ frontmixer, frontstream ])

# link new client to mixers
def link_new_client(client):

    create_frontmixer_queue()

    print("  setting up mixers for new client "+client.name)

    # create surface/audio mixers for _all_ clients that don't have one yet
    # needs to loop through all clients for the case where 2 or more clients
    # appear simultaneously, otherwise there are no mixers to link to
    # FIXME: this is a hack, might be solved by using the testsources initially?
    if len(clients) >= 2:
        for c in clients:
            clients[c].create_mixer("surface", new_element("compositor",{"background":"black"}), new_element("videoconvert"),
            new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=1280,height=720,framerate=15/1")}))
            clients[c].create_mixer(  "audio", new_element("audiomixer"), new_element("audioconvert"),
            new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=U8,rate=48000,channels=1")}))

    # add missing frontmixer links
    client.link_to_front()

    # add missing surface/audio mixer links
    client.link_all_streams(clients)

    dump_debug("final")

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
        print("Client "+source+": all input/output elements complete.")
        link_new_client(client)

