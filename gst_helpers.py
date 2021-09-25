#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib

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
        # FIXME what about duplicate names in child bins?
        if pipeline.get_by_name(item.name) == None:
            pipeline.add(item)
        item.sync_state_with_parent()
        # TODO: add a way to link pads instead of elements?
        if prev != None:
            prev.link(item)
        prev = item

# capture and handle bus messages
def bus_call(bus, message, loop):
    t = message.type
    #print(message.src,t)
    if t == Gst.MessageType.EOS:
        print("End-of-stream, quitting.\n")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print("Error: %s: %s\n" % (err, debug))
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print("Warning: %s: %s\n" % (err, debug))
    elif t == Gst.MessageType.NEW_CLOCK:
        print("New clock source selected.\n")
    elif t == Gst.MessageType.CLOCK_LOST:
        print("Clock lost!\n")
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
    # write out debug dot file (needs envvar GST_DEBUG_DUMP_DOT_DIR set)
    Gst.debug_bin_to_dot_file(pipeline,Gst.DebugGraphDetails(15),name)

def get_by_name(name):
    return pipeline.get_by_name(name)

# initialize pipeline and mainloop
def init_pipeline(callback):

    global pipeline,mainloop

    Gst.init(None)
    pipeline = Gst.Pipeline()

    # kick things off
    pipeline.set_state(Gst.State.PLAYING)
    mainloop = GLib.MainLoop()
    pipeline.connect("element-added",callback)

    # listen for bus messages
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, mainloop)

# test sources as stream placeholders
def add_test_sources(main=False):

    bgcol = 0xFF00FF00
    wave  = "ticks"

    if main:
        bgcol = 0xFFFF00FF
        wave  = "sine"

    if main:
        frontsrc = [ new_element("videotestsrc",{"is-live":True,"pattern":"smpte"}) ]
        surfsrc  = [ new_element("videotestsrc",{"is-live":True,"pattern":"ball","background-color":bgcol}) ]
        audiosrc = [ new_element("audiotestsrc",{"is-live":True,"wave":wave}) ]
    else:
        frontsrc = [ new_element("v4l2src",{"do-timestamp":True,"device":"/dev/video0" }), new_element("videorate"), new_element("videoconvert") ]
        #frontsrc = [ new_element("videotestsrc",{"is-live":True,"pattern":"smpte"}) ]
        surfsrc  = [ new_element("videotestsrc",{"is-live":True,"pattern":"ball","background-color":bgcol}) ]
        #surfsrc  = [ new_element("v4l2src",{"do-timestamp":True,"device":"/dev/video10"}), new_element("videorate"), new_element("videoconvert") ]
        audiosrc = [ new_element("alsasrc",{"do-timestamp":True}), new_element("audiorate"), new_element("audioconvert") ]

    add_and_link(frontsrc + [
        new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=640,height=360,framerate=15/1")}),
        new_element("tee",{"allow-not-linked":True},"fronttestsource")
    ])

    add_and_link(surfsrc + [
        new_element("capsfilter",{"caps":Gst.Caps.from_string("video/x-raw,format=YV12,width=1280,height=720,framerate=15/1")}),
        new_element("tee",{"allow-not-linked":True},"surfacetestsource")
    ])

    add_and_link(audiosrc + [
        new_element("capsfilter",{"caps":Gst.Caps.from_string("audio/x-raw,format=U8,rate=48000,channels=1")}),
        new_element("tee",{"allow-not-linked":True},"audiotestsource")
    ])

def run_mainloop():
    mainloop.run()
