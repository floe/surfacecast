var frontoutput;
var surfaceoutput;
var websocketConnection;
var webrtcPeerConnection;
var webrtcConfiguration;
var reportError = function (errmsg) { console.error(errmsg); }
var datastream;
var canvas,surfacesource,frontsource;
var canvasctx,sourcectx;
var canvasstream;

var audiotrans;
var surfacetrans;
var fronttrans;
var remotemap;
var frontstream;
var surfacestream;

function onLocalDescription(desc) {
  var mapping = { };
  for (const trans of webrtcPeerConnection.getTransceivers()) {
    if (trans.sender.track.id == surfacetrans) mapping[trans.mid] = "surface";
    if (trans.sender.track.id == fronttrans  ) mapping[trans.mid] = "front";
    if (trans.sender.track.id == audiotrans  ) mapping[trans.mid] = "audio";
  }
  webrtcPeerConnection.setLocalDescription(desc).then(function() {
    websocketConnection.send(JSON.stringify({ "type": "sdp", "data": webrtcPeerConnection.localDescription, "mapping": mapping }));
  }).catch(reportError);
}


function onIncomingSDP(sdp) {
  console.log("Incoming SDP: " + JSON.stringify(sdp));
  webrtcPeerConnection.setRemoteDescription(sdp).catch(reportError);
  webrtcPeerConnection.createAnswer().then(onLocalDescription).catch(reportError);
}


function onIncomingICE(ice) {
  ice.sdpMid = null; // sdpMid is currently fake, ignore
  var candidate = new RTCIceCandidate(ice);
  //console.log("Incoming ICE: " + JSON.stringify(ice));
  webrtcPeerConnection.addIceCandidate(candidate).catch(reportError);
}


function onAddRemoteStream(event) {
  console.log(event);

  if (remotemap[event.transceiver.mid] == "front") {
    frontstream.addTrack(event.track);
    frontoutput.srcObject = frontstream;
    frontoutput.play().catch(reportError);
  }

  if (remotemap[event.transceiver.mid] == "audio") {
    frontstream.addTrack(event.track);
  }

  if (remotemap[event.transceiver.mid] == "surface") {
    surfacestream.addTrack(event.track);
    surfaceoutput.srcObject = surfacestream;
    surfaceoutput.play().catch(reportError);
  }
}


function onIceCandidate(event) {
  if (event.candidate == null)
    return;

  //console.log("Sending ICE candidate out: " + JSON.stringify(event.candidate));
  websocketConnection.send(JSON.stringify({ "type": "ice", "data": event.candidate }));
}

function getLocalStreams() {
  // courtesy of https://stackoverflow.com/a/33770858
  var vidconst = { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" };
  return navigator.mediaDevices.enumerateDevices().then(devices => {
    const cams = devices.filter(device => device.kind == "videoinput");
    const mics = devices.filter(device => device.kind == "audioinput");
    const constraints = { video: (cams.length > 0 ? vidconst : false), audio: mics.length > 0 };
    return navigator.mediaDevices.getUserMedia(constraints);
  });
}


function onServerMessage(event) {
  var msg;

  try {
    msg = JSON.parse(event.data);
  } catch (e) {
    return;
  }

  if ("mapping" in msg) {
    remotemap = msg.mapping;
    console.log(remotemap);
  }
  switch (msg.type) {
    case "sdp": onIncomingSDP(msg.data); break;
    case "ice": onIncomingICE(msg.data); break;
    default: break;
  }
}

function playStream() {
  var l = window.location;
  var wsUrl = "wss://" + l.hostname + ":" + l.port + "/ws";

  frontstream = new MediaStream();
  surfacestream = new MediaStream();

  if (!webrtcPeerConnection) {

    getLocalStreams().then( (stream) => {
      
      webrtcPeerConnection = new RTCPeerConnection(webrtcConfiguration);
      webrtcPeerConnection.ontrack = onAddRemoteStream;
      webrtcPeerConnection.onicecandidate = onIceCandidate;
      webrtcPeerConnection.ondatachannel = function(event) { event.channel.onmessage = function(event) { console.log(event); } }

      datastream = webrtcPeerConnection.createDataChannel("events");
      datastream.onopen = function(event) { datastream.send("Hi from "+navigator.userAgent); }

      var audiotrack = stream.getAudioTracks()[0];
      audiotrans = audiotrack.id;
      webrtcPeerConnection.addTrack(audiotrack);

      var vidtracks = stream.getVideoTracks();
      var fronttrack = null;
      if (vidtracks.length > 0) {
        fronttrack = vidtracks[0];
        console.log("using camera track for front");
      } else {
        canvasstream = frontsource.captureStream(15);
        fronttrack = canvasstream.getVideoTracks()[0];
        console.log("using fake front stream");
        //fronttrack.contentHint = "detail";
      }
      fronttrans = fronttrack.id;
      webrtcPeerConnection.addTrack(fronttrack);

      canvasstream = surfacesource.captureStream(15);
      canvastrack = canvasstream.getVideoTracks()[0];
      canvastrack.contentHint = "detail";
      surfacetrans = canvastrack.id;
      webrtcPeerConnection.addTrack(canvastrack, stream);

      websocketConnection = new WebSocket(wsUrl);
      websocketConnection.addEventListener("message", onServerMessage);
      console.log("Capture setup complete.");
    } );
  }
}

function get_context(canvas,w,h,fillstyle) {
  var context = canvas.getContext("2d");
  canvas.width  = w;
  canvas.height = h;
  context.fillStyle = fillstyle;
  context.fillRect(0,0,w,h);
  return context;
}

window.onload = function() {

  // output element for incoming front stream
  frontoutput = document.getElementById("frontoutput");
  // output element for incoming surface stream
  surfaceoutput = document.getElementById("surfaceoutput");

  // canvas/canvasctx is the primary, visible drawing surface
  canvas = document.getElementById("surfacecanvas");
  canvasctx = get_context(canvas,1280,720,"rgba(0,255,0,0)"); // FIXME: hardcoded dimensions

  // surfacesource/sourcectx is the surface stream source (invisible drawing surface with green background)
  surfacesource = document.getElementById("surfacesource");
  sourcectx = get_context(surfacesource,1280,720,"rgba(0,255,0,255)"); // FIXME: hardcoded dimensions

  // some interactive handler needed to give stream higher priority?
  canvas.onmousemove = function(ev) { sourcectx.strokeStyle = "red"; sourcectx.fillStyle = "red"; sourcectx.fillRect(10, 10, 20, 20); }

  webrtcConfiguration = { 'iceServers': [{urls:"stun:stun.l.google.com:19302"},{urls:"stun:stun.ekiga.net"}] };
  playStream();

  if (typeof canvas_init  === "function") canvas_init();
  if (typeof drawStickers === "function") setTimeout( () => { requestAnimationFrame(drawStickers); }, 2000 );
};