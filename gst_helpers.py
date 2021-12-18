#!/usr/bin/env python3

import gi,logging,os
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib
from functools import partial, partialmethod

# TODO this should be a class Pipeline

# global objects
pipeline = None
mainloop = None


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
    # TODO: handle more message types? see https://lazka.github.io/pgi-docs/index.html#Gst-1.0/flags.html#Gst.MessageType
    t = message.type
    #logging.debug(message.src,t)
    if t == Gst.MessageType.EOS:
        logging.info("Pipeline reached end-of-stream, quitting.")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        logging.error("Pipeline error: %s: %s", err, debug)
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        logging.warning("Pipeline warning: %s: %s", err, debug)
    elif t == Gst.MessageType.NEW_CLOCK:
        logging.info("New pipeline clock source selected.")
    elif t == Gst.MessageType.CLOCK_LOST:
        logging.warning("Pipeline clock lost!")
    return True

# convenience function to link request pads
def link_request_pads(el1, tpl1, el2, tpl2, do_queue=True):

    pad1 = el1.get_static_pad(tpl1)
    if pad1 == None:
        pad1 = el1.request_pad(el1.get_pad_template(tpl1), None, None)

    pad2 = el2.get_static_pad(tpl2)
    if pad2 == None:
        pad2 = el2.request_pad(el2.get_pad_template(tpl2), None, None)

    if do_queue:
        queue = new_element("queue")#,{"max-size-time":200000000})
        pipeline.add(queue)
        queue.sync_state_with_parent()
        pad1.link(queue.get_static_pad("sink"))
        queue.get_static_pad("src").link(pad2)
    else:
        pad1.link(pad2)
    return pad2

# link to input-selector and activate new link
def link_to_inputselector(el1, tpl1, el2):
    pad = link_request_pads(el1,tpl1,el2,"sink_%u",do_queue=False)
    el2.set_property("active-pad", pad)
    return pad

def dump_debug(name="debug"):
    if os.getenv("GST_DEBUG_DUMP_DOT_DIR") == None:
        return
    logging.info("Writing graph snapshot to "+name+".dot")
    # write out debug dot file (needs envvar GST_DEBUG_DUMP_DOT_DIR set)
    Gst.debug_bin_to_dot_file(pipeline,Gst.DebugGraphDetails(15),name)

def get_by_name(name):
    return pipeline.get_by_name(name)

# initialize pipeline and mainloop
def init_pipeline(callback,mylevel=0):

    global pipeline,mainloop

    # add an extra logging level (courtesy of https://stackoverflow.com/a/55276759/838719)
    logging.TRACE = 5
    logging.addLevelName(logging.TRACE, "TRACE")
    logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)
    logging.trace = partial(logging.log, logging.TRACE)

    # configure the logger
    loglevels = { 0: logging.INFO, 1: logging.DEBUG, 2: logging.TRACE }
    logging.basicConfig(format="%(levelname)s:: %(message)s",level=loglevels[mylevel])

    Gst.init(None)
    pipeline = Gst.Pipeline()

    # kick things off
    mainloop = GLib.MainLoop()
    pipeline.connect("element-added",callback)

    # listen for bus messages
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, mainloop)

# test sources as stream placeholders
def add_test_sources(frontdev="",surfdev="",fake=False,bgcol=0xFF00FF00,wave="ticks"):

    if fake:
        frontsrc = "videotestsrc is-live=true pattern=smpte ! timeoverlay" if frontdev == "" else frontdev
        surfsrc  = "videotestsrc is-live=true pattern=ball background-color="+str(bgcol)+" ! timeoverlay" if surfdev == "" else surfdev
        audiosrc = "audiotestsrc is-live=true wave="+wave
    else:
        # FIXME: if a virtual device (e.g. v4l2loopback is used here, then it needs to use RGB pixel format, otherwise caps negotiation fails
        frontsrc = "v4l2src do-timestamp=true device="+frontdev+" ! videorate ! videoconvert" 
        surfsrc  = "v4l2src do-timestamp=true device="+surfdev+"  ! videorate ! videoconvert" 
        audiosrc = "alsasrc do-timestamp=true" # "audiorate ! audioconvert"

    logging.debug("  Front Source: "+frontsrc)
    logging.debug("Surface Source: "+surfsrc)
    logging.debug("  Audio Source: "+audiosrc)

    add_and_link([ Gst.parse_bin_from_description( frontsrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=640,height=360,framerate=15/1")}),
        new_element("tee",{"allow-not-linked":True},"fronttestsource")
    ])

    add_and_link([ Gst.parse_bin_from_description( surfsrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=1280,height=720,framerate=15/1")}),
        new_element("tee",{"allow-not-linked":True},"surfacetestsource")
    ])

    add_and_link([ Gst.parse_bin_from_description( audiosrc, True ),
        new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=U8,rate=48000,channels=1")}),
        new_element("tee",{"allow-not-linked":True},"audiotestsource")
    ])


def run_mainloop():
    pipeline.set_state(Gst.State.PLAYING)
    mainloop.run()

def quit_mainloop():
    mainloop.quit()
