# SurfaceStreams

A framework to mix and distribute live video feeds from interactive surfaces via WebRTC.

[add picture here]

SurfaceStreams consists of a mixing server, and one or more clients. Each clients sends one audiostream and two video streams: a plain old webcam feed of the user called the _front stream_, and a second feed of a rectified interactive surface called the _surface stream_. The surface stream is expected to have any background removed and chroma-keyed with 100% bright green.

The mixing server then composes a new surface stream for each client, consisting of the layered surface streams of the _other_ clients, and streams that back to each client (along with a single combined front stream of all individual front streams arranged side-by-side).

## Clients

* standalone Python client
  * any two V4L2 video sources (also virtual ones, e.g. from https://github.com/floe/surfacecast)
* HTML5 client
  * virtual drawing board surface
* VR client
  * tbd

## Requirements

* Mixing server & standalone client
  * Ubuntu 20.04 LTS (Python 3.8, GStreamer 1.16)
  * Debian 11 "Bullseye" (Python 3.9, GStreamer 1.18)
  * Install dependencies: `sudo apt install gstreamer1.0-libav gir1.2-soup-2.4 gir1.2-gstreamer-1.0 gir1.2-gst-plugins-bad-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-nice-0.1 libnice10 gstreamer1.0-nice gstreamer1.0-plugins-bad`

* HTML5 client
  * Firefox 78 ESR (Note: remember to enable OpenH264 plugin in about:plugins)
  * Firefox 94/95
  * Chrome 92
  * Chromium (buggy)
  * Safari (buggy?)
