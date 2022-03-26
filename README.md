# SurfaceStreams

A framework to mix and distribute live video feeds from interactive surfaces via WebRTC.

![table surface with projected message](assets/teaser.jpg)
Image credit: (c) Stadt Regensburg, (c) Stefan Effenhauser

SurfaceStreams consists of a mixing server, and one or more clients. Each clients sends one audiostream and two video streams: a plain old webcam feed of the user called the _front stream_, and a second feed of a rectified interactive surface called the _surface stream_. The surface stream is expected to have any background removed and chroma-keyed with 100% bright green.

The mixing server then composes a new surface stream for each client, consisting of the layered surface streams of the _other_ clients, and streams that back to each client (along with a single combined front stream of all individual front streams arranged side-by-side).

## HowTo

Here's an example walkthrough of how to connect an interactive surface with a browser client:

 * on a server host with sufficient CPU resources, run the mixing backend: `./webrtc_server.py`
 * start the browser client:
   * with Chrome or Firefox, go to `https://${SERVER_HOST}:8080/stream.html`
   * allow access to camera/microphone
   * you should then see your own webcam stream and a pink surface with a bouncing ball after a few seconds, and hear a pilot tone
   * try doodling on the pink surface (left mouse button draws, right button erases)
 * start the interactive surface:
   * setup and calibrate [SurfaceCast](https://github.com/floe/surfacecast) to stream the surface on virtual camera `/dev/video20` (see Usage - Example 2)
   * run the Python client: `./webrtc_client.py -t ${SERVER_HOST} -s /dev/video20 -f /dev/video0` (or whatever device your plain webcam is)
   * put the `surface` window as fullscreen on the surface display, and the `front` window on the front display
 * connect additional browser and/or surface clients (up to 4 in total)

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
  * Install dependencies: `sudo apt install gstreamer1.0-libav gir1.2-soup-2.4 gir1.2-gstreamer-1.0 gir1.2-gst-plugins-bad-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-nice-0.1 libnice10 gstreamer1.0-nice gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly`

* HTML5 client
  * Firefox 78 ESR (Note: remember to enable OpenH264 plugin in `about:plugins`)
  * Firefox 94 - 96
  * Chrome 92 - 97

## Known issues

  * Server
    * The server will repeatedly issue the warning `[...]: loop detected in the graph of bin 'pipeline0'!!`, which can be safely ignored.
    * Some race conditions when setting up the mixers still seem to be present, but hard to pin down. This happens particularly when a client connects within a few seconds of the previous client, before negotiation has completed.
  * Python Client
    * Using webcams as live sources (e.g. for the front stream) is somewhat hit-and-miss and depends on the pixel formats the webcam can deliver. Reliable results so far only with 24-bit RGB or 16-bit YUYV/YUV2 (see also [issue #4](https://github.com/floe/surfacestreams/issues/4)). The front/face cam needs to support 640x360 natively, the surface cam needs to support 1280x720 natively. Good results with Logitech C270 (front/face) and C920 (surface). Note: environment variable `GST_V4L2_USE_LIBV4L2=1` can sometimes be used to fix format mismatch issues.
    * The Python client has a noticeable delay (sometimes on the order of 30 seconds) before the surface stream finally starts running, unlike e.g. the browser client (see also [issue #2](https://github.com/floe/surfacestreams/issues/2)). Once it runs, the delay is negligible, but the waiting time until things synchronize is iffy.
    * A Raspberry Pi 4 is just barely fast enough to handle the incoming and outgoing streams _plus_ the SurfaceCast perspective transform. Overclocking to 1800 core/600 GPU is recommended.
  * HTML5 client
    * not working on Chromium (non-free codec problem, see [issue #8](https://github.com/floe/surfacestreams/issues/8))
    * not working on Safari (reason unknown, see [issue #6](https://github.com/floe/surfacestreams/issues/6))
