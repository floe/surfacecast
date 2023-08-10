#!/usr/bin/env python3

import gi,logging,os,signal
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib
from functools import partial, partialmethod

# TODO this should be a class Pipeline

# global objects
pipeline = None
mainloop = None
bus = None


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
        logging.error("Pipeline error: %s: %s", err, debug)
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        logging.warning("Pipeline warning: %s: %s", err, debug)
    return True

# shortcut to request pad
def get_request_pad(el,tpl):
    return el.request_pad(el.get_pad_template(tpl), None, None)

# create single mixer for front stream
def create_frontmixer_queue():

    logging.info("Creating frontmixer subqueue...")

    frontmixer  = new_element("compositor",{"latency":50000000},myname="frontmixer")
    capsfilter  = new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=I420,width=1280,height=720,framerate=15/1")})
    frontstream = new_element("tee",{"allow-not-linked":True},myname="frontstream")

    add_and_link([ frontmixer, capsfilter, frontstream ])

    frontsource = get_by_name("fronttestsource")
    pad1 = get_request_pad(frontsource,"src_%u")
    pad2 = get_request_pad(frontmixer,"sink_%u")
    pad1.link(pad2)

# write out debug dot file (needs envvar GST_DEBUG_DUMP_DOT_DIR set)
def dump_debug(name="surfacestreams"):
    if os.getenv("GST_DEBUG_DUMP_DOT_DIR") == None:
        logging.info("Cannot dump graph, GST_DEBUG_DUMP_DOT_DIR is unset.")
        return
    logging.info("Writing graph snapshot to "+name+".dot")
    Gst.debug_bin_to_dot_file(pipeline,Gst.DebugGraphDetails.ALL,name)

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
def add_test_sources(frontdev="",surfdev="",audiodev="",fake=False,bgcol=0xFF00FF00,wave="ticks",sw=1280,sh=720):

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
        new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=I420,width=640,height=360,framerate=15/1")}),
        new_element("tee",{"allow-not-linked":True},"fronttestsource")
    ])

    add_and_link([ Gst.parse_bin_from_description( surfsrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string(f"video/x-raw,format=AYUV,width={sw},height={sh},framerate=15/1")}),
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
