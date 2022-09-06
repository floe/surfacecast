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

# client object pool
clients = {}

# position offsets for 4 front streams
# FIXME: how to handle > 4 clients?
offsets = [
    (640,360), # bottom right
    (  0,  0), # top left
    (640,  0), # top right
    (  0,360)  # bottom left
]


class BaseClient:

    def __init__(self,name,wrb):

        self.wrb = wrb
        self.name = name
        self.queues = []
        self.reqpads = []

        # link to sources
        for name in ["surface","front","audio"]:
            self.link_request_pads(get_by_name(name+"testsource"),"src_%u",self.wrb.bin,"sink_"+name,do_queue=False)

    # get a (new) pad from an element
    def get_pad(self, el, tpl):

        pad = el.get_static_pad(tpl)

        # pad doesn't exist yet, so request a new one (and store it)
        if pad == None:
            pad = get_request_pad(el,tpl)
            self.reqpads.append(pad)
        # we have a static pad, check if it's already linked
        else:
            peer = pad.get_peer()
            if peer:
                peer.unlink(pad)

        return pad

    # convenience function to link request pads (and keep track of pads/queues)
    def link_request_pads(self, el1, tpl1, el2, tpl2, do_queue=True, qp={}):

        pad1 = self.get_pad(el1,tpl1)
        pad2 = self.get_pad(el2,tpl2)

        if do_queue:
            queue = new_element("queue",qp)
            add_and_link([queue])
            pad1.link(queue.get_static_pad("sink"))
            queue.get_static_pad("src").link(pad2)
            self.queues.append(queue)
        else:
            pad1.link(pad2)

        return pad2


class Client(BaseClient):

    def __init__(self,name,wrb):

        super().__init__(name,wrb)
        self.outputs = {}
        self.mixers = {}
        clients[name] = self

    def remove(self):
        logging.info("Removing client: "+self.name)
        clients.pop(self.name)

        # pause, unlink, and remove the mixers
        logging.debug("  Removing mixers...")
        for i in self.mixers:
            mixer = self.mixers[i]
            mixer.set_state(Gst.State.NULL)
            for p in mixer.sinkpads:
                peer = p.get_peer()
                if peer:
                    peer.unlink(p)
            remove_element(mixer)
        self.mixers.clear()

        # pause the bin
        self.wrb.bin.set_state(Gst.State.NULL)

        # pause, unlink, and remove the output buffers
        logging.debug("  Removing outputs...")
        for i in self.outputs:
            out_tee = self.outputs[i]
            out_tee.set_state(Gst.State.NULL)
            for p in out_tee.srcpads:
                p.unlink(p.get_peer())
            remove_element(out_tee)
        self.outputs.clear()

        # remove the bin
        logging.debug("  Removing main bin...")
        remove_element(self.wrb.bin)

        # remove the alphafilter, if exists
        alpha = get_by_name("alpha_"+self.name)
        if alpha:
            alpha.set_state(Gst.State.NULL)
            remove_element(alpha)

        # remove the textoverlay, if exists
        text = get_by_name("text_"+self.name)
        if text:
            text.set_state(Gst.State.NULL)
            remove_element(text)

        # remove queues from link_request_pad
        logging.debug("  Removing queues...")
        for q in self.queues:
            q.set_state(Gst.State.NULL)
            remove_element(q)
        self.queues.clear()

        # remove request pads
        logging.debug("  Removing request pads...")
        for p in self.reqpads:
            el = p.get_parent_element()
            if el != None:
                el.release_request_pad(p)
        self.reqpads.clear()

        self.wrb.bin = None
        self.wrb.wrb = None
        self.wrb = None

        logging.info("Client "+self.name+" unlinked.")

    # create mixer & converter
    def create_mixer(self,mtype,mixer,caps):

        if mtype in self.mixers:
            return

        logging.info("    creating "+mtype+" mixer for client "+self.name)

        self.mixers[mtype] = mixer
        self.mixers[mtype+"_caps"] = caps
        add_and_link([mixer,caps])

        self.link_request_pads(caps,"src",self.wrb.bin,"sink_"+mtype,do_queue=False)
        self.link_request_pads(get_by_name(mtype+"testsource"),"src_%u",mixer,"sink_%u")

    # link client to frontmixer
    def link_to_front(self):

        # FIXME: frontstream is separately encoded for each client ATM, should be one single encoder
        logging.info("    linking client "+self.name+" to frontmixer")

        # link frontstream tee to client
        self.link_request_pads(get_by_name("frontstream"),"src_%u",self.wrb.bin,"sink_front",do_queue=False)

        # sanity check (important for sink client)
        if not "front" in self.outputs:
            return

        # request and link pads from tee and frontmixer
        sinkpad = self.link_request_pads(self.outputs["front"],"src_%u",get_by_name("frontmixer"),"sink_%u")

        # set xpos/ypos properties on pad according to sequence number
        padnum = int(sinkpad.get_name().split("_")[1]) % len(offsets)
        sinkpad.set_property("xpos",offsets[padnum][0])
        sinkpad.set_property("ypos",offsets[padnum][1])

    # helper function to link source tees to destination mixers
    def link_streams_oneway(self,dest,prefix,qparams):

        # sanity check (important for sink client)
        if not prefix in self.outputs:
            return

        logging.info("    linking client "+self.name+" to "+prefix+"mixer "+dest.name)
        sinkpad = self.link_request_pads(self.outputs[prefix],"src_%u",dest.mixers[prefix],"sink_%u",qp=qparams)

        # for the "main" surface, destination mixer pad needs zorder = 0
        if prefix == "surface" and "main" in self.wrb.flags:
            logging.info("    fixing zorder for main client")
            sinkpad.set_property("zorder",0)

    # link all other clients to this mixer, this client to other mixers
    def link_streams(self,prefix,qparams):

        for c in clients:

            if c == self.name: # skip own ssrc
                if not "own" in self.wrb.flags or prefix == "audio":
                    continue

            other = clients[c]

            # for every _other_ mixer, link my tee to that mixer
            self.link_streams_oneway(other,prefix,qparams)

            # for every _other_ tee, link that tee to my mixer
            other.link_streams_oneway(self,prefix,qparams)

    # link new client to mixers
    def link_new_client(self):

        logging.info("  setting up mixers for new client "+self.name)

        # create surface/audio mixers
        self.create_mixer("surface", new_element("compositor",{"background":"black"}), new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=AYUV,width=1280,height=720,framerate=15/1")}))
        self.create_mixer(  "audio", new_element("audiomixer"                       ), new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=S16LE,rate=48000,channels=1")}))

        # add missing frontmixer links
        self.link_to_front()

        # add missing surface/audio mixer links
        # TODO: figure out the queue parameters (if any?)
        self.link_streams("surface",{}) # {"max-size-buffers":1})
        self.link_streams("audio",{}) # {"max-size-time":100000000})

# new top-level element added to pipeline
def on_element_added(thebin, element):

    # check format: {input,output}_IPADDR_PORT_{surface,front,audio}
    elname = element.get_name().split("_")
    if len(elname) != 4:
        return

    direction = elname[0]
    source = elname[1]+"_"+elname[2]
    stype = elname[3]
    #logging.debug("New element: "+direction+" "+source+" "+stype)

    client = clients[source]
    # TODO: perhaps store the alpha element in outputs as well?
    if direction == "output":
        client.outputs[stype] = element

    # are all outputs in place?
    if len(client.outputs) == 3:
        logging.info("Client "+source+": all input/output elements complete.")
        client.link_new_client()
