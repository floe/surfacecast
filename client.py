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

# last DTS for compositor pads
last_pts = {}

# pad probe for fixing timestamps (UUUUGLY hack, use after link_request_pads:)
def probe_callback(pad,info,pdata):
    buf = info.get_buffer()
    if buf.pts == Gst.CLOCK_TIME_NONE:
        logging.warn("Fixing decoded buffer with null timestamp")
        buf.pts = last_pts[pad]
    else:
        last_pts[pad] = buf.pts
    return Gst.PadProbeReturn.OK

class BaseClient:

    def __init__(self,name,wrb):

        self.wrb = wrb
        self.name = name
        self.queues = []
        self.reqpads = []

        # link to sources
        for name in ["surface","front","audio"]:
            logging.debug("Linking "+name+" test source to webrtcbin")
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
    def link_request_pads(self, el1, tpl1, el2, tpl2, do_queue=True, qp={"leaky":"downstream","max-size-time":100000000}):

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

    def __init__(self,name,wrb,sw=1280,sh=720,mutex=None):

        super().__init__(name,wrb)
        self.outputs = {}
        self.mixers = {}
        self.mutex = mutex
        self.sw = sw
        self.sh = sh
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
                other = p.get_peer()
                if other != None:
                    p.unlink(other)
            remove_element(out_tee)
        self.outputs.clear()

        # remove the bin
        logging.debug("  Removing main bin...")
        remove_element(self.wrb.bin)

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

        # remove stale references
        self.wrb.cleanup()
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
        sinkpad.add_probe(Gst.PadProbeType.BUFFER, probe_callback, None)

        # set xpos/ypos properties on pad according to sequence number
        # FIXME: can this actually lead to front streams overlapping after some reconnects?
        padnum = int(sinkpad.get_name().split("_")[1]) % len(offsets)
        sinkpad.set_property("xpos",offsets[padnum][0])
        sinkpad.set_property("ypos",offsets[padnum][1])

    # helper function to link source tees to destination mixers
    def link_streams_oneway(self,dest,prefix):

        # sanity check (important for sink client)
        if not prefix in self.outputs:
            return

        logging.info("    linking client "+self.name+" to "+prefix+"mixer "+dest.name)
        sinkpad = self.link_request_pads(self.outputs[prefix],"src_%u",dest.mixers[prefix],"sink_%u")
        sinkpad.add_probe(Gst.PadProbeType.BUFFER, probe_callback, None)

        # "inter-client" queues and reqpads need to be deleted by either side, whichever is removed
        # first. so add the newly created items to the respective list for the other client as well.
        dest.queues.append (self.queues [-1])
        dest.reqpads.append(self.reqpads[-1])

        # for the "main" surface, destination mixer pad needs zorder = 0
        if prefix == "surface" and "main" in self.wrb.flags:
            logging.info("    fixing zorder for main client")
            sinkpad.set_property("zorder",0)

    # link all other clients to this mixer, this client to other mixers
    def link_streams(self,prefix):

        for c in clients:

            if c == self.name: # skip own ssrc
                if prefix == "surface" and "own" in self.wrb.flags:
                    self.link_streams_oneway(self,prefix)
                continue

            other = clients[c]

            # for every _other_ mixer, link my tee to that mixer
            self.link_streams_oneway(other,prefix)

            # for every _other_ tee, link that tee to my mixer
            other.link_streams_oneway(self,prefix)

    # link new client to mixers
    def link_new_client(self):

        logging.info("  setting up mixers for new client "+self.name)

        # create surface/audio mixers
        self.create_mixer("surface", new_element("compositor",{"latency":100000000,"background":"black"}), new_element("capsfilter",{"caps":Gst.Caps.from_string(f"video/x-raw,format=AYUV,width={self.sw},height={self.sh}")}))
        self.create_mixer(  "audio", new_element("audiomixer",{"latency":100000000}                     ), new_element("capsfilter",{"caps":Gst.Caps.from_string(f"audio/x-raw,format=S16LE,rate=48000,channels=1")}))

        # add missing frontmixer links
        self.link_to_front()

        # add missing surface/audio mixer links
        self.link_streams("surface")
        self.link_streams("audio")

        # unlock the new connection mutex
        if self.mutex != None:
            self.mutex.release()

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
    if direction == "output":
        client.outputs[stype] = element

    # are all outputs in place?
    if len(client.outputs) == 3:
        logging.info("Client "+source+": all input/output elements complete.")
        client.link_new_client()
