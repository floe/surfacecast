#!/usr/bin/python3

import sys,gi,json,re
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, GstWebRTC, GstSdp

from gst_helpers import *

VENCODER="queue max-size-buffers=1 ! x264enc bitrate=600 speed-preset=ultrafast tune=zerolatency key-int-max=15 ! video/x-h264,profile=constrained-baseline ! queue max-size-time=100000000 ! h264parse ! rtph264pay config-interval=-1 ! application/x-rtp,media=video,encoding-name=H264,"
AENCODER="queue ! opusenc ! rtpopuspay ! queue max-size-time=100000000 ! application/x-rtp,media=audio,encoding-name=OPUS,"

# TODO make stun server configurable? maybe print firewall info?
bindesc="webrtcbin name=webrtcbin stun-server=stun://stun.l.google.com:19302 "+\
  "videoconvert name=front   ! "+VENCODER+"payload=96 ! webrtcbin. "+\
  "audioconvert name=audio   ! "+AENCODER+"payload=97 ! webrtcbin. "+\
  "videoconvert name=surface ! "+VENCODER+"payload=98 ! webrtcbin. "

response_type = {
    "offer":  GstWebRTC.WebRTCSDPType.OFFER,
    "answer": GstWebRTC.WebRTCSDPType.ANSWER
}

# FIXME: apparently it's not a good idea to directly use payload numbers,
# but still no idea how to identify the streams individually otherwise...
payload = {
    96: "front",
    97: "audio",
    98: "surface"
}

# extract MediaIDs (mid) from SDP and match with payload ID
def get_mids_from_sdp(sdptext):

    result = { }
    lines = sdptext.splitlines()
    plnum = 0

    for line in lines:

        if line.startswith("m="):
            try:
                plnum = int(line.split(" ")[-1])
            except:
                plnum = 0

        if not plnum in payload:
            continue

        if line.startswith("a=mid:"):
            mid = line.split(":")[1]
            result[mid] = payload[plnum]

    return result

class WebRTCPeer:

    def __init__(self, connection, address, msghandler = None, is_client=False, is_main=False):

        self.connection = connection
        self.is_client = is_client
        self.data_channel = None
        self.address = address
        self.mapping = None
        self.msghandler = msghandler

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

        # send message to server if main client
        if is_main:
            message = json.dumps({"type":"msg","data":"main"})
            self.connection.send_text(message)

    # message on WebRTC data channel
    def on_dc_message(self, wrb, message):
        logging.debug("New data channel message: "+message)

    # new data channel created
    def on_data_channel(self, wrb, data_channel):
        logging.info("New data channel created.")
        self.data_channel = data_channel
        self.data_channel.connect("on-message-string", self.on_dc_message)
        self.data_channel.connect("on-message-data",   self.on_dc_message)
        # FIXME: doesn't seem to send anything?
        self.data_channel.emit("send-data",GLib.Bytes.new("Hi!".encode("utf-8")))
        self.data_channel.emit("send-string","Hi!")

    # ICE connection candidate received, forward to peer
    def on_ice_candidate(self, wrb, index, candidate):
        icemsg = json.dumps({"type":"ice","data":{"sdpMLineIndex":index,"candidate":candidate}})
        logging.debug("New local ICE candidate: "+icemsg)
        self.connection.send_text(icemsg)

    # format negotiation requested
    def on_negotiation_needed(self, wrb):

        # request offer or answer, depending on role
        kind = "answer" if self.is_client else "offer"
        logging.info("Negotiation requested, creating "+kind+"...")
        promise = Gst.Promise.new_with_change_func(self.on_negotiation_created,kind)
        self.wrb.emit("create-"+kind, None, promise)

    # WebRTCBin has created a format negotiation offer
    def on_negotiation_created(self, promise, kind):
        
        reply = promise.get_reply()
        if reply == None:
            # Note: this is okay on client side, the initial on-negotiation-needed signal will fire before
            # the remote offer has been received, so it has to be re-triggered once the offer has arrived
            logging.info("Received empty "+kind+" from webrtcbin, retrying...")
            return

        result = reply.get_value(kind)
        self.wrb.emit("set-local-description", result, None)

        text = result.sdp.as_text()

        # 1.16 generates sprop-parameter-sets containing the substring "DAILS", 1.18 contains "DAwNS".
        # This can confuse caps negotiation on the client side, and subsequently transceiver matching.
        # To avoid this issue altogether, get rid of the entire SPS parameter in the generated SDP.
        text = re.sub(";sprop-parameter-sets=.*","",text)

        # FIXME this is an extremly ugly hack, treating SDP as "string soup"
        # see https://stackoverflow.com/q/65408744/838719 for some background
        # a (slightly) better solution would be to use the result.sdp object
        mapping = get_mids_from_sdp(text)

        message = json.dumps({"type":"sdp","data":{"type":kind,"sdp":text},"mapping":mapping})
        logging.debug("Outgoing SDP: " + message)
        self.connection.send_text(message)

    # new pad appears on WebRTCBin element
    def on_pad_added(self, wrb, pad):

        caps = pad.get_current_caps()
        struct = caps.get_structure(0)
        res, ssrc = struct.get_uint("ssrc")

        if pad.direction != Gst.PadDirection.SRC or not res:
            return

        logging.info("New incoming stream, linking to decodebin...")
        decodebin = new_element("decodebin",myname="decodebin_"+self.mapping[str(ssrc)])
        decodebin.connect("pad-added", self.on_decodebin_pad)

        self.wrb.parent.add(decodebin) # TODO or self.bin.add(...)?
        decodebin.sync_state_with_parent()
        pad.link(decodebin.get_static_pad("sink"))

    def on_decodebin_pad(self, decodebin, pad):

        if not pad.has_current_caps():
            return

        name = decodebin.get_name().split("_")[1]
        logging.info("Handling new decodebin pad of type: "+name)

        # add named ghostpads ("src_front" etc.)
        ghostpad = Gst.GhostPad.new("src_"+name,pad)
        ghostpad.set_active(True)
        decodebin.parent.add_pad(ghostpad)

        alpha = None
        if name == "surface" and self.msghandler and not "main" in self.msghandler.flags:
            alpha = new_element("alpha", { "method": "green" } )

        tee = new_element("tee",{"allow-not-linked":True},myname="output_"+self.address+"_"+name)
        add_and_link([alpha,tee])
        last = tee if alpha == None else alpha
        ghostpad.link(last.get_static_pad("sink"))

    # incoming Websocket message
    def on_ws_message(self, connection, mtype, data):

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

            logging.debug("Incoming SDP: " + json.dumps(msg))

            res, sdpmsg = GstSdp.sdp_message_new_from_text(sdp)
            # as client, we need to parse an OFFER, as server, we need to parse an ANSWER
            result = GstWebRTC.WebRTCSessionDescription.new(response_type[stype], sdpmsg)
            self.wrb.emit("set-remote-description", result, None)

            # mapping contains only MediaIDs, but we need SSRC locally
            if "mapping" in msg:
                self.mapping = msg["mapping"]

                # lookup corresponding SSRC for each MediaID
                for i in range(sdpmsg.medias_len()):
                    media = sdpmsg.get_media(i)
                    mid  = media.get_attribute_val("mid").split(" ")[0]
                    ssrc = media.get_attribute_val("ssrc")
                    if ssrc and mid in self.mapping:
                        self.mapping[ssrc.split(" ")[0]] = self.mapping[mid]

                logging.debug("Incoming stream mapping:"+json.dumps(self.mapping))

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
            logging.debug("Incoming ICE candidate: " + candidate)

        if msg["type"] == "msg" and self.msghandler:
            self.msghandler.process(msg["data"])
            logging.debug("Incoming websocket message: "+msg["data"])
