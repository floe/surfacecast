#!/usr/bin/python3

import sys,gi,json,re,time
gi.require_version('GLib', '2.0')
gi.require_version('Gst',  '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GLib, Gst, GstWebRTC, GstSdp

from gst_helpers import *

VENCODER="queue max-size-time=50000000 leaky=downstream ! x264enc bitrate=1500 speed-preset=ultrafast tune=zerolatency key-int-max=15 ! video/x-h264,profile=constrained-baseline,stream-format=avc ! queue ! "
# TODO: VP8 has better compatibility (esp. wrt to Firefox), but the encoder performance and error recovery suck, switch back to H.264 for now
#VENCODER="queue ! vp8enc threads=2 deadline=2000 target-bitrate=1500000 ! queue ! "
HWENCODER='video/x-raw,format=I420 ! queue ! v4l2h264enc extra-controls="controls,video_bitrate=1500000,video_bitrate_mode=1" ! video/x-h264,profile=constrained-baseline,level=(string)3.1 ! queue ! h264parse ! '
AENCODER="queue max-size-time=50000000 leaky=downstream ! opusenc bitrate-type=vbr audio-type=voice packet-loss-percentage=20 inband-fec=true ! queue ! opusparse ! "

RTPVIDEO="h264parse config-interval=-1 ! rtph264pay config-interval=1 mtu=1200 ! application/x-rtp,media=video,encoding-name=H264,"
#RTPVIDEO="rtpvp8pay ! application/x-rtp,media=video,encoding-name=VP8,"
RTPAUDIO="rtpopuspay mtu=1200 ! application/x-rtp,media=audio,encoding-name=OPUS,"
FILESINK="matroskamux name=mux offset-to-zero=true ! filesink sync=true location="

bindesc="webrtcbin name=webrtcbin bundle-policy=max-bundle stun-server=%s "+\
  "videoconvert name=front   ! "+VENCODER+RTPVIDEO+"payload=96 ! webrtcbin. "+\
  "audioconvert name=audio   ! "+AENCODER+RTPAUDIO+"payload=97 ! webrtcbin. "+\
  "videoconvert name=surface ! "+VENCODER+RTPVIDEO+"payload=98 ! webrtcbin. "

filebin=FILESINK+"%s "+\
  "videoconvert name=front   ! "+VENCODER+" mux. "+\
  "audioconvert name=audio   ! "+AENCODER+" mux. "+\
  "videoconvert name=surface ! "+VENCODER+" mux. "

viewbin=\
  "videoconvert name=front   ! fpsdisplaysink "+\
  "audioconvert name=audio   ! autoaudiosink  "+\
  "videoconvert name=surface ! fpsdisplaysink "

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
                plnum = int(line.split(" ")[3])
            except:
                plnum = 0

        if not plnum in payload:
            continue

        if line.startswith("a=mid:"):
            mid = line.split(":")[1]
            result[mid] = payload[plnum]

        if line.startswith("a=ssrc:"):
            ssrc = line.split(":")[1].split(" ")[0]
            result[ssrc] = payload[plnum]

    return result

# base class: bin with 3 sink ghostpads
class StreamSink:

    def __init__(self, name, param, bin_desc=filebin):

        self.name = name
        self.flags = {}
        bin_desc = bin_desc % param

        logging.info("Setting up stream handler for "+name)
        logging.trace("Bin contents: "+bin_desc)

        self.bin = Gst.parse_bin_from_description(bin_desc,False)
        self.bin.set_name("bin_"+name)
        add_and_link([self.bin])

        # add ghostpads (proxy-pads)
        for name in ["surface","front","audio"]:

            logging.debug("Creating "+name+" ghostpad for "+self.name)

            element = self.bin.get_by_name(name)
            realpad = element.get_static_pad("sink")

            ghostpad = Gst.GhostPad.new("sink_"+name,realpad)
            ghostpad.set_active(True)
            self.bin.add_pad(ghostpad)


# specialization: containing WebRTCBin and _lots_ of plumbing
class WebRTCPeer(StreamSink):

    def __init__(self, connection, name, stun, is_client=False, flags=[]):

        super().__init__(name,stun,bindesc)

        self.connection = connection
        self.is_client = is_client
        self.data_channel = None
        self.mapping = None
        self.filters = []
        self.flags = {}

        self.connection.connect("message",self.on_ws_message)
        self.wrb = self.bin.get_by_name("webrtcbin")
        # self.get_stats() # FIXME uncomment to get vast amounts of streaming statistics

        # connect signals (note: negotiation-needed will initially be empty on client side)
        self.wrb.connect("on-negotiation-needed", self.on_negotiation_needed)
        self.wrb.connect("on-ice-candidate",      self.on_ice_candidate     )
        self.wrb.connect("on-data-channel",       self.on_data_channel      )
        self.wrb.connect("pad-added",             self.on_pad_added         )

        # create the data channel
        self.data_channel = self.wrb.emit("create-data-channel", "events", None)
        self.data_channel.connect("on-open", self.on_channel_open)

        # send flags to server
        for flag in flags:
            message = json.dumps({"type":"msg","data":flag})
            self.connection.send_text(message)

        # improve error correction for all transceivers (FEC/NACK)
        index = 0
        while trans := self.wrb.emit("get-transceiver",index):
            logging.debug("Adjust FEC/NACK for transceiver "+str(index))
            trans.set_property("fec-type",GstWebRTC.WebRTCFECType.ULP_RED)
            trans.set_property("fec-percentage",20)
            if index != 1: # FIXME Chrome can't do audio NACK?
                trans.set_property("do-nack",True)
            index += 1

    # remove leftover object references
    def cleanup(self):
        for f in self.filters:
            f.set_state(Gst.State.NULL)
            remove_element(f)
        self.filters = None
        self.data_channel = None
        self.in_channel = None
        self.connection = None
        self.bin = None
        self.wrb = None

    # application-level message
    def process(self, msg):
        self.flags.update(msg)
        logging.debug("Setting flags for "+self.name+": "+str(msg))

    # outgoing data channel is open
    def on_channel_open(self, channel):
        hello = "Hi from "+self.name
        self.data_channel.emit("send-data",GLib.Bytes.new(hello.encode("utf-8")))
        self.data_channel.emit("send-string",hello)

    # message on WebRTC data channel
    def on_dc_message(self, channel, message):
        logging.debug("New data channel message: "+str(message))

    # new data channel created
    def on_data_channel(self, wrb, data_channel):
        logging.info("New incoming data channel created.")
        self.in_channel = data_channel
        self.in_channel.connect("on-message-string", self.on_dc_message)
        self.in_channel.connect("on-message-data",   self.on_dc_message)

    # ICE connection candidate received, forward to peer
    def on_ice_candidate(self, wrb, index, candidate):
        # throw in a fake sdpMid attribute to work around https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/-/issues/1174
        icemsg = json.dumps({"type":"ice","data":{"sdpMLineIndex":index,"candidate":candidate}}) #,"sdpMid":"video0"}})
        logging.trace("New local ICE candidate: "+icemsg)
        self.connection.send_text(icemsg)

    # format negotiation requested
    def on_negotiation_needed(self, wrb):

        # request offer or answer, depending on role
        kind = "answer" if self.is_client else "offer"
        logging.info("Negotiation requested, creating "+kind+"...")
        promise = Gst.Promise.new_with_change_func(self.on_negotiation_created,kind)
        self.wrb.emit("create-"+kind, None, promise)

    # get the streaming stats
    def get_stats(self):
        promise = Gst.Promise.new_with_change_func(self.stats_ready)
        if self.wrb != None:
            self.wrb.emit("get-stats", None, promise)
        return False

    def stats_ready(self,promise):
        GLib.timeout_add(1000,self.get_stats)
        reply = promise.get_reply()
        logging.debug("Streaming stats: "+dump_structure(reply)) #.replace("\\",""))

    # WebRTCBin has created a format negotiation offer
    def on_negotiation_created(self, promise, kind):
        
        reply = promise.get_reply()
        if reply == None or reply.get_value(kind) == None:
            # Note: this is okay on client side, the initial on-negotiation-needed signal will fire before
            # the remote offer has been received, so it has to be re-triggered once the offer has arrived
            logging.debug("Received empty "+kind+" from webrtcbin, retrying...")
            return

        result = reply.get_value(kind)
        text = result.sdp.as_text()

        # Different GStreamer versions generate slightly different sprop-parameter-sets.
        # This can confuse caps negotiation on the client side, and subsequently transceiver matching.
        # To avoid this issue altogether, get rid of the entire SPS parameter in the generated SDP.
        text = re.sub(";?sprop-parameter-sets=.*?(;|\r\n)","\\1",text)

        # FIXME this is an extremly ugly hack, treating SDP as "string soup"
        # see https://stackoverflow.com/q/65408744/838719 for some background
        # a (slightly) better solution would be to use the result.sdp object
        mapping = get_mids_from_sdp(text)

        # check whether all 3 media blocks already have MID & SSRC, otherwise retry
        if not len(mapping) >= 6:
            logging.debug("Not all MIDs/SSRCs present, retrying negotiation...")
            time.sleep(1)
            self.on_negotiation_needed(self.wrb)
            return

        # SDP is now good, so confirm as local session description...
        self.wrb.emit("set-local-description", result, None)

        # ... and send to peer.
        message = json.dumps({"type":"sdp","data":{"type":kind,"sdp":text},"mapping":mapping})
        logging.debug("Outgoing SDP "+kind+": " + text)
        logging.debug("Outgoing stream mapping: "+ str(mapping))
        self.connection.send_text(message)

    # new pad appears on WebRTCBin element
    def on_pad_added(self, wrb, pad):
        # to be overwritten in subclass
        print("NOPE")

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

            logging.info("Received SDP " + stype + ", parsing...")
            logging.debug("Incoming SDP: " + sdp)

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

                logging.debug("Incoming stream mapping: "+json.dumps(self.mapping))

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
            logging.trace("Incoming ICE candidate: " + json.dumps(msg))

        if msg["type"] == "msg":
            self.process(msg["data"])

# decoding/filtering of incoming streams
class WebRTCDecoder(WebRTCPeer):

    def __init__(self, connection, name, stun, is_client=False, flags=[], surf_pipe=""):
        super().__init__(connection, name, stun, is_client, flags)
        self.surf_pipe = surf_pipe

    # new pad appears on WebRTCBin element
    def on_pad_added(self, wrb, pad):

        caps = pad.get_current_caps()
        struct = caps.get_structure(0)
        res, ssrc = struct.get_uint("ssrc")

        if pad.direction != Gst.PadDirection.SRC or not res:
            return

        name = self.mapping[str(ssrc)]
        logging.info("New incoming "+name+" stream, linking...")
        logging.trace("Stream caps: "+caps.to_string())

        if name == "surface" and self.surf_pipe != "":
            # Note: the first element in surf_pipe needs to have a sink pad
            logging.debug("Creating bin from description: "+self.surf_pipe)
            decodebin = Gst.parse_bin_from_description( self.surf_pipe, True )
        else:
            logging.debug("Creating default decodebin...")
            decodebin = new_element("decodebin",{"force-sw-decoders":True},myname="decodebin_"+name)
            decodebin.connect("pad-added", self.on_decodebin_pad)

        self.wrb.parent.add(decodebin)
        decodebin.sync_state_with_parent()
        pad.link(decodebin.get_static_pad("sink"))

    def create_filters(self,name):

        # prepare the output tee (and return on client side)
        current = [ new_element("tee",{"allow-not-linked":True},myname="output_"+self.name+"_"+name) ]
        padname = "sink"

        if self.is_client:
            return current,padname

        # add alpha filtering (unless main client)
        if name == "surface" and not "main" in self.flags:
            logging.info("Adding alpha filter for "+self.name+" surface output")
            current.insert(0,new_element("alpha", { "method": "green" }, myname="alpha_"+self.name ))

        # add perspective transform if requested
        if name == "surface" and "perspective" in self.flags:
            logging.info("Adding perspective transform for "+self.name+" surface output")
            params = [ float(f) for f in self.flags["perspective"].split(",") ]
            current.insert(0,new_element("perspective",{"matrix":params},myname="persp_"+self.name))
            current.insert(0,new_element("videoconvert"))

        # add a nickname text overlay if given
        if name == "front" and "nick" in self.flags:
            logging.info("Adding nickname overlay for "+self.name+" front output")
            current.insert(0,new_element("textoverlay",{"halignment":"left","valignment":"bottom","text":self.flags["nick"]},myname="text_"+self.name))
            padname = "video_sink" # FIXME ugly, but probably unavoidable

        return current,padname

    def on_decodebin_pad(self, decodebin, pad):

        if not pad.has_current_caps():
            return

        name = decodebin.get_name().split("_")[1]
        logging.info("Handling new decodebin pad of type: "+name)
        logging.trace("Stream caps: "+pad.get_current_caps().to_string())

        # add named ghostpads ("src_front" etc.)
        ghostpad = Gst.GhostPad.new("src_"+name,pad)
        ghostpad.set_active(True)
        decodebin.parent.add_pad(ghostpad)

        # prepare the output tee and optional filters
        chain,padname = self.create_filters(name)
        self.filters.extend(chain)

        # add to pipeline and link everything together
        add_and_link(chain)
        ghostpad.link(chain[0].get_static_pad(padname))

