#!/usr/bin/env python3

import gi,logging,os,signal,re
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib
from functools import partial, partialmethod

# TODO this should be a class Pipeline

# global objects
pipeline = None
mainloop = None
bus = None

# client object pool
clients = {}

# conveniently create a new GStreamer element and set parameters
def new_element(element_name,parameters={},myname=None):
    element = Gst.ElementFactory.make(element_name,myname)
    for key,val in parameters.items():
        element.set_property(key,val)
    return element

# convenience function to add a list of elements to the pipeline and link them in sequence
def add_and_link(elements):
    prev = None
    for item in elements:
        if item == None:
            continue
        if pipeline.get_by_name(item.name) == None:
            pipeline.add(item)
        item.sync_state_with_parent()
        if prev != None:
            prev.link(item)
        prev = item

# capture and handle bus messages
def bus_call(bus, message, loop):
    t = message.type
    logging.trace(str(message.src)+str(t))
    if t == Gst.MessageType.EOS:
        logging.info("Pipeline reached end-of-stream, quitting.")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        # FIXME this is apparently unrecoverable? need to kill the client
        if "SCTP association went into error state" in debug:
           pattern = re.search(r"GstBin:bin_(.*)/GstWebRTCBin",debug)
           cid = pattern[1]
           logging.error("SCTP timeout for client %s, disconnecting...",cid)
           clients[cid].remove()
           return True
        logging.error("Pipeline error: %s: %s", err, debug)
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        logging.warning("Pipeline warning: %s: %s", err, debug)
    return True

# shortcut to request pad
def get_request_pad(el,tpl):
    return el.request_pad(el.get_pad_template(tpl), None, None)

# create single mixer for front stream
def create_frontmixer_queue(fps=15):

    logging.info("Creating frontmixer subqueue...")

    frontmixer  = new_element("compositor",{"latency":50000000},myname="frontmixer")
    capsfilter  = new_element("capsfilter",{"caps":Gst.Caps.from_string(f"video/x-raw,format=I420,width=1280,height=720,framerate={fps}/1")})
    frontstream = new_element("tee",{"allow-not-linked":True},myname="frontstream")

    add_and_link([ frontmixer, capsfilter, frontstream ])

    frontsource = get_by_name("fronttestsource")
    pad1 = get_request_pad(frontsource,"src_%u")
    pad2 = get_request_pad(frontmixer,"sink_%u")
    pad1.link(pad2)

# position offsets and src/dest dimensions for 1-4 front streams
# FIXME: how to handle > 4 clients?
all_offsets = [
    [
    ],[
        (  0,   0, 1280, 720, 1280, 720)  # single fullscreen
    ],[
        (  0,   0,  640, 720,  640, 720), # pillarbox left
        (640,   0,  640, 720,  640, 720)  # pillarbox right
    ],[
        (  0,   0,  640, 720,  640, 720), # pillarbox left
        (640,   0, 1280, 720,  640, 360), # top right
        (640, 360, 1280, 720,  640, 360)  # bottom right
    ],[
        (  0,   0, 1280, 720,  640, 360), # top left
        (640,   0, 1280, 720,  640, 360), # top right
        (  0, 360, 1280, 720,  640, 360), # bottom left
        (640, 360, 1280, 720,  640, 360)  # bottom right
    ]
]

# use all_offsets to arrange the incoming frontstreams
def arrange_frontstreams():

    fm = get_by_name("frontmixer")
    count = 0
    offsets = all_offsets[len(fm.sinkpads)-1]

    # set xpos/ypos/offset properties on pad according to sequence number
    for pad in fm.sinkpads:

        padnum = int(pad.get_name().split("_")[1])
        if padnum == 0: # skip testsource pad
            continue
        padnum = count % len(offsets)
        count += 1

        # set the target rectangle
        pad.set_property("xpos",offsets[padnum][0])
        pad.set_property("ypos",offsets[padnum][1])
        pad.set_property("width",offsets[padnum][4])
        pad.set_property("height",offsets[padnum][5])

        # set the source width and offset
        cc = Gst.Structure.new_empty("cc") # FIXME hardcoded source image width
        cc.set_value("GstVideoConverter.src-x",int((1280-offsets[padnum][2])/2))
        cc.set_value("GstVideoConverter.src-width",offsets[padnum][2])
        pad.set_property("converter-config",cc)

# write out debug dot file (needs envvar GST_DEBUG_DUMP_DOT_DIR set)
def dump_debug(name="surfacecast"):
    if os.getenv("GST_DEBUG_DUMP_DOT_DIR") == None:
        logging.info("Cannot dump graph, GST_DEBUG_DUMP_DOT_DIR is unset.")
        return
    logging.info("Writing graph snapshot to "+name+".dot")
    Gst.debug_bin_to_dot_file(pipeline,Gst.DebugGraphDetails.ALL,name)

# convert a gststructure to formatted text (FIXME: incomplete)
def dump_structure(struct,level=0):
    result = "structure "+struct.get_name()+":\n"
    for i in range(struct.n_fields()):
        name = struct.nth_field_name(i)
        result += "  "+name+": "
        field = struct.get_value(name)
        print(str(field))
    return result

def get_by_name(name):
    return pipeline.get_by_name(name)

def remove_element(item):
    return pipeline.remove(item)

# initialize pipeline and mainloop
def init_pipeline(callback,mylevel=0):

    global pipeline,mainloop,bus

    # add an extra logging level (courtesy of https://stackoverflow.com/a/55276759/838719)
    logging.TRACE = 5
    logging.addLevelName(logging.TRACE, "TRACE")
    logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)
    logging.trace = partial(logging.log, logging.TRACE)

    # configure the logger
    loglevels = { 0: logging.INFO, 1: logging.DEBUG, 2: logging.TRACE }
    logging.basicConfig(format="[%(levelname)-5s] %(message)s",level=loglevels[mylevel])

    # signal handler to dump graph dot file on SIGUSR1
    signal.signal(signal.SIGUSR1, lambda a,b: dump_debug())

    Gst.init(None)
    pipeline = Gst.Pipeline()

    # kick things off
    mainloop = GLib.MainLoop()
    pipeline.connect("element-added",callback)

    # listen for bus messages
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, mainloop)

def connect_bus(msgtype, callback, *args):
    bus.connect(msgtype, callback, *args)

# test sources as stream placeholders
def add_test_sources(frontdev="",surfdev="",audiodev="",fake=False,bgcol=0xFF00FF00,wave="ticks",sw=1280,sh=720,fps=15):

    if fake:
        frontsrc = "videotestsrc is-live=true pattern=smpte ! timeoverlay text="+wave if frontdev == "" else frontdev
        surfsrc  = "videotestsrc is-live=true pattern=ball background-color="+str(bgcol)+" ! timeoverlay" if surfdev == "" else surfdev
        audiosrc = "audiotestsrc is-live=true wave="+wave if audiodev == "" else audiodev
    else:
        # FIXME: if a virtual device (e.g. v4l2loopback is used here, then it needs to use RGB pixel format, otherwise caps negotiation fails
        frontsrc = "v4l2src do-timestamp=true device="+frontdev+" ! videorate ! videoconvert ! videocrop top=-1 bottom=-1 left=-1 right=-1"
        surfsrc  = "v4l2src do-timestamp=true device="+surfdev+"  ! videorate ! videoconvert ! videocrop top=-1 bottom=-1 left=-1 right=-1"
        audiosrc = "alsasrc do-timestamp=true" # "audiorate ! audioconvert"

    logging.debug("  Front Source: "+frontsrc)
    logging.debug("Surface Source: "+surfsrc)
    logging.debug("  Audio Source: "+audiosrc)

    add_and_link([ Gst.parse_bin_from_description( frontsrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string(f"video/x-raw,format=I420,width=1280,height=720,framerate={fps}/1")}),
        new_element("tee",{"allow-not-linked":True},"fronttestsource")
    ])

    add_and_link([ Gst.parse_bin_from_description( surfsrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string(f"video/x-raw,format=AYUV,width={sw},height={sh},framerate={fps}/1")}),
        new_element("tee",{"allow-not-linked":True},"surfacetestsource")
    ])

    add_and_link([ Gst.parse_bin_from_description( audiosrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=S16LE,rate=48000,channels=1")}),
        new_element("tee",{"allow-not-linked":True},"audiotestsource")
    ])


def run_mainloop():
    pipeline.set_state(Gst.State.PLAYING)
    logging.info("Pipeline starting (library version "+Gst.version_string()+")")
    mainloop.run()

def quit_mainloop():
    pipeline.set_state(Gst.State.NULL)
    Gst.deinit()
    mainloop.quit()
