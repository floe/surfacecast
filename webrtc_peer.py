#!/usr/bin/python3

import sys,gi,json
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, GstWebRTC, GstSdp

from gst_helpers import *

VENCODER="queue max-size-buffers=1 ! x264enc bitrate=600 speed-preset=ultrafast tune=zerolatency key-int-max=15 ! video/x-h264,profile=constrained-baseline ! queue max-size-time=100000000 ! h264parse ! rtph264pay config-interval=-1 ! application/x-rtp,media=video,encoding-name=H264,"
AENCODER="queue ! opusenc ! rtpopuspay ! queue max-size-time=100000000 ! application/x-rtp,media=audio,encoding-name=OPUS,"

# TODO implement the stun servers (again) for actual internet connections
# stun-server=stun://" STUN_SERVER " "
bindesc="webrtcbin name=webrtcbin "+\
  "videoconvert name=front   ! "+VENCODER+"payload=96 ! webrtcbin. "+\
  "audioconvert name=audio   ! "+AENCODER+"payload=97 ! webrtcbin. "+\
  "videoconvert name=surface ! "+VENCODER+"payload=98 ! webrtcbin. "

response_type = {
    "offer":  GstWebRTC.WebRTCSDPType.OFFER,
    "answer": GstWebRTC.WebRTCSDPType.ANSWER
}

payload = {
    96: "front",
    97: "audio",
    98: "surface"
}

# TODO: how to connect specific mixers etc. to each webrtcbin?

class WebRTCPeer:

    def __init__(self, connection, address, is_client=False):

        self.connection = connection
        self.is_client = is_client
        self.data_channel = None
        self.address = address

        self.bin = Gst.parse_bin_from_description(bindesc,False)
        self.bin.set_name("bin_"+address)
        add_and_link([self.bin])

        self.wrb = self.bin.get_by_name("webrtcbin")

        # add ghostpads (proxy-pads) and input-selectors for the converters
        for name in ["surface","front","audio"]:

            element = self.bin.get_by_name(name)
            realpad = element.get_static_pad("sink")
            ghostpad = Gst.GhostPad.new("sink_"+name,realpad)
            ghostpad.set_active(True)
            self.bin.add_pad(ghostpad)

            selector = new_element("input-selector",myname="input_"+self.address+"_"+name)
            add_and_link([selector])
            selector.get_static_pad("src").link(ghostpad)

            # TODO: source name should be configurable
            link_request_pads(get_by_name(name+"testsource"),"src_%u",selector,"sink_%u")

        self.connection.connect("message",self.on_ws_message)

        # connect signals (note: negotiation-needed will initially be empty on client side)
        self.wrb.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.wrb.connect("on-ice-candidate",      self.on_ice_candidate     )
        self.wrb.connect("on-data-channel",       self.on_data_channel      )
        self.wrb.connect("pad-added",             self.on_pad_added         )

        # create the data channel
        self.wrb.emit("create-data-channel", "events", None)

    # message on WebRTC data channel
    def on_dc_message(self, wrb, message):
        print("New data channel message: "+message)

    # new data channel created
    def on_data_channel(self, wrb, data_channel):
        print("New data channel created...")
        self.data_channel = data_channel
        self.data_channel.connect("on-message-string", self.on_dc_message)
        self.data_channel.emit("send-string","Hi!")

    # ICE connection candidate received, forward to peer
    def on_ice_candidate(self, wrb, index, candidate):
        icemsg = json.dumps({"type":"ice","data":{"sdpMLineIndex":index,"candidate":candidate}})
        self.connection.send_text(icemsg)

    # format negotiation requested
    def on_negotiation_needed(self, wrb):
        kind = "answer" if self.is_client else "offer"
        print("Negotiation requested, creating "+kind+"...")
        promise = Gst.Promise.new_with_change_func(self.on_negotiation_created,kind)
        self.wrb.emit("create-"+kind, None, promise)

    # WebRTCBin has created a format negotiation offer
    def on_negotiation_created(self, promise, kind):
        
        reply = promise.get_reply()
        if reply == None:
            # Note: this is okay on client side, the initial on-negotiation-needed signal will fire before
            # the remote offer has been received, so it has to be re-triggered once the offer has arrived
            print("Warning: received empty "+kind+" from webrtcbin!")
            return

        result = reply.get_value(kind)
        self.wrb.emit("set-local-description", result, None)

        text = result.sdp.as_text()
        message = json.dumps({"type":"sdp","data":{"type":kind,"sdp":text}})
        self.connection.send_text(message)

    # new pad appears on WebRTCBin element
    def on_pad_added(self, wrb, pad):

        caps = pad.get_current_caps()
        struct = caps.get_structure(0)
        res, plnum = struct.get_int("payload")

        if pad.direction != Gst.PadDirection.SRC or not res:
            return

        print("New incoming stream, linking to decodebin...")
        decodebin = new_element("decodebin",myname="decodebin_"+payload[plnum])
        decodebin.connect("pad-added", self.on_decodebin_pad)

        self.wrb.parent.add(decodebin) # or self.bin.add(...)?
        decodebin.sync_state_with_parent()
        pad.link(decodebin.get_static_pad("sink"))

    def on_decodebin_pad(self, decodebin, pad):

        if not pad.has_current_caps():
            #print ("no caps), ignoring.")
            return

        name = decodebin.get_name().split("_")[1]
        print("Handling new decodebin pad of type: "+name)

        # add named ghostpads ("src_front" etc.)
        ghostpad = Gst.GhostPad.new("src_"+name,pad)
        ghostpad.set_active(True)
        decodebin.parent.add_pad(ghostpad)

        tee = new_element("tee",{"allow-not-linked":True},myname="output_"+self.address+"_"+name)
        add_and_link([tee])
        ghostpad.link(tee.get_static_pad("sink"))

    # incoming Websocket message
    def on_ws_message(self, connection, mtype, data):

        #print(data.get_data())
        try:
            msg = json.loads(data.get_data())
        except:
            return

        if msg["type"] == "sdp":
            reply = msg["data"]
            stype = reply["type"]
            sdp = reply["sdp"]
            if len(sdp) == 0:
                return

            res, sdpmsg = GstSdp.sdp_message_new_from_text(sdp)
            # as client, we need to parse an OFFER, as server, we need to parse an ANSWER
            result = GstWebRTC.WebRTCSessionDescription.new(response_type[stype], sdpmsg)
            self.wrb.emit("set-remote-description", result, None)

            # on the client side, we need to manually trigger the negotiation answer
            if self.is_client:
                self.on_negotiation_needed(self.wrb)

        if msg["type"] == "ice":
            ice = msg["data"]
            candidate = ice["candidate"]
            if len(candidate) == 0:
                return
            sdpmlineindex = ice["sdpMLineIndex"]
            self.wrb.emit("add-ice-candidate", sdpmlineindex, candidate)

