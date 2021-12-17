var html5VideoElement;
var html5VideoElement2;
var websocketConnection;
var webrtcPeerConnection;
var webrtcConfiguration;
var reportError;
var datastream;
var canvas;
var context,c2;
var canvasstream;
var mousedown;
var mycolor;
var x,y;

var audiotrans;
var surfacetrans;
var fronttrans;
var remotemap;
var frontstream;
var surfacestream;

function paint(ctx, centerX, centerY, clearcolor, clearmode) {
  const radius = (mousedown == 1) ? 5 : 20;
  ctx.beginPath();
  ctx.lineWidth = radius;
  ctx.strokeStyle = (mousedown == 1) ? mycolor : clearcolor;
  ctx.fillStyle = ctx.strokeStyle
  ctx.globalCompositeOperation = (mousedown == 1) ? "source-over" : clearmode;
  ctx.moveTo(x,y);
  ctx.lineTo(centerX,centerY);
  ctx.stroke();
  ctx.arc(centerX, centerY, radius/2, 0, 2 * Math.PI, false);
  ctx.fill();
  ctx.closePath();
}


function onCanvasDown(evt) { x = evt.offsetX; y = evt.offsetY; mousedown = evt.buttons; }
function onCanvasUp  (evt) { onCanvasMove(evt);                mousedown = 0;           }

function onCanvasMove(evt) {

  if (mousedown == 0) return;
  const centerX = evt.offsetX;
  const centerY = evt.offsetY;

  paint(context, centerX, centerY, "rgba(0,  0,0,255)", "destination-out");
  paint(c2,      centerX, centerY, "rgba(0,255,0,255)", "source-over"    );

  x = centerX;
  y = centerY;
}


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
  var candidate = new RTCIceCandidate(ice);
  //console.log("Incoming ICE: " + JSON.stringify(ice));
  webrtcPeerConnection.addIceCandidate(candidate).catch(reportError);
}


function onAddRemoteStream(event) {
  console.log(event);

  if (remotemap[event.transceiver.mid] == "front") {
    frontstream.addTrack(event.track);
    html5VideoElement.srcObject = frontstream;
    html5VideoElement.play().catch(reportError);
  }

  if (remotemap[event.transceiver.mid] == "audio") {
    frontstream.addTrack(event.track);
  }

  if (remotemap[event.transceiver.mid] == "surface") {
    surfacestream.addTrack(event.track);
    html5VideoElement2.srcObject = surfacestream;
    html5VideoElement2.play().catch(reportError);
  }
}


function onIceCandidate(event) {
  if (event.candidate == null)
    return;

  //console.log("Sending ICE candidate out: " + JSON.stringify(event.candidate));
  websocketConnection.send(JSON.stringify({ "type": "ice", "data": event.candidate }));
}

function getLocalStreams() {
  var constraints = {video: { width: { ideal: 640 }, height: { ideal: 360 }, aspectRatio: { ideal: 1.7777777778 }, facingMode: "user" }, audio: true};
  return navigator.mediaDevices.getUserMedia(constraints);
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

function playStream(videoElement, hostname, port, path, configuration, reportErrorCB) {
  var l = window.location;
  var wsHost = (hostname != undefined) ? hostname : l.hostname;
  var wsPort = (port != undefined) ? port : l.port;
  var wsPath = (path != undefined) ? path : "ws";
  if (wsPort)
    wsPort = ":" + wsPort;
  var wsUrl = "wss://" + wsHost + wsPort + "/" + wsPath;

  html5VideoElement = videoElement;
  webrtcConfiguration = configuration;
  reportError = (reportErrorCB != undefined) ? reportErrorCB : function(text) {};
  frontstream = new MediaStream();
  surfacestream = new MediaStream();

  if (!webrtcPeerConnection) {
    getLocalStreams().then( (stream) => {
      
      webrtcPeerConnection = new RTCPeerConnection(webrtcConfiguration);
      webrtcPeerConnection.ontrack = onAddRemoteStream;
      webrtcPeerConnection.onicecandidate = onIceCandidate;

      datastream = webrtcPeerConnection.createDataChannel("events");
      datastream.onopen = function(event) { datastream.send("Hi!"); console.log("Hi!"); }
      // datastream.onmessage = ...

      audiotrack = stream.getAudioTracks()[0];
      audiotrans = audiotrack.id;
      webrtcPeerConnection.addTrack(audiotrack);

      fronttrack = stream.getVideoTracks()[0];
      fronttrans = fronttrack.id;
      webrtcPeerConnection.addTrack(fronttrack);

      canvasstream = canvas2.captureStream(15);
      canvastrack = canvasstream.getVideoTracks()[0];
      canvastrack.contentHint = "detail";
      surfacetrans = canvastrack.id;
      webrtcPeerConnection.addTrack(canvastrack, stream);
      // make sure that the canvas stream starts by triggering a delayed paint operation
      setTimeout(() => { c2.fillRect(0, 0, canvas2.width, canvas2.height); }, 1000);

      websocketConnection = new WebSocket(wsUrl);
      websocketConnection.addEventListener("message", onServerMessage);
      //websocketConnection.onopen = function(event) { websocketConnection.send("Hoi!"); };
    } );
  }
}

window.onload = function() {
  var vidstream = document.getElementById("stream");
  html5VideoElement2 = document.getElementById("stream2");
  canvas = document.getElementById("canvas");
  //fixCanvas(canvas);
  context = canvas.getContext("2d");
  canvas.width=1280;
  canvas.height=720;
  context.fillStyle = "rgba(0,255,0,0)";
  context.fillRect(0, 0, canvas.width, canvas.height);

  canvas.onmousedown = onCanvasDown;
  canvas.ontouchstart = onCanvasDown;
  canvas.onmouseup   = onCanvasUp;
  canvas.ontouchend = onCanvasUp;
  canvas.onmousemove = onCanvasMove;

  canvas.addEventListener("contextmenu", function(e) { e.preventDefault(); } );
  var config = { 'iceServers': [{urls:"stun:stun.l.google.com:19302"},{urls:"stun:stun.ekiga.net"}] };
  playStream(vidstream, null, null, null, config, function (errmsg) { console.error(errmsg); });
  colors = ["red", "cyan", "yellow", "blue", "magenta" ];
  mycolor = colors[Math.floor(Math.random() * colors.length)];

  canvas2 = document.getElementById("canvas2");
  c2 = canvas2.getContext("2d");
  canvas2.width=1280;
  canvas2.height=720;

  c2.fillStyle = "rgba(0,255,0,255)";
  c2.fillRect(0, 0, canvas2.width, canvas2.height);
};
