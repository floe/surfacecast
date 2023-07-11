var frontoutput;
var surfaceoutput;
var websocketConnection;
var webrtcPeerConnection;
var webrtcConfiguration;
var reportError;
var datastream;
var canvas,surfacesource,frontsource;
var context,c2,c3;
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
var windowstream = null;
var desktopsource;

var audioCtx;
var analyser;
var source;

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


function onCanvasDown(evt) { x = evt.offsetX; y = evt.offsetY; mousedown = (evt.buttons == undefined) ? 1 : evt.buttons; }
function onCanvasUp  (evt) { onCanvasMove(evt);                mousedown = 0;                                            }

function onCanvasMove(evt) {

  if (mousedown == 0) return;

  if (evt.type == "touchmove") {
    evt.preventDefault();
    evt.offsetX = evt.changedTouches[0].pageX;
    evt.offsetY = evt.changedTouches[0].pageY;
  }

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
  var vidconst = { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: "user" };
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

function updateAudioFeedback() {

    var target = document.getElementById("mouth");
    if (target === null) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    scale = (dataArray[1]/255.0)+ (dataArray[2]/255.0);

    target.object3D.scale.set(scale,scale,scale);
    setTimeout(updateAudioFeedback,50);
}

function drawVideo() {
  c2.drawImage( desktopsource, 0, 0, 1280, 720 );
  c2.drawImage( canvas, 0, 0, 1280, 720 );
  // 15 FPS rate-limiting, cf. https://stackoverflow.com/q/19764018
  setTimeout( () => { requestAnimationFrame(drawVideo); }, 1000/15 );
}

function playStream(configuration, reportErrorCB) {
  var l = window.location;
  var wsUrl = "wss://" + l.hostname + ":" + l.port + "/ws";

  webrtcConfiguration = configuration;
  reportError = (reportErrorCB != undefined) ? reportErrorCB : function(text) {};
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

      audiotrack = stream.getAudioTracks()[0];
      audiotrans = audiotrack.id;
      webrtcPeerConnection.addTrack(audiotrack);

      // from https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Visualizations_with_Web_Audio_API
      audioCtx = new AudioContext();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      setTimeout(updateAudioFeedback,50);

      var vidtracks = stream.getVideoTracks();
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
      // make sure that the canvas stream starts by triggering a delayed paint operation
      setTimeout(() => { c2.fillRect(0, 0, surfacesource.width, surfacesource.height); }, 1000);

      websocketConnection = new WebSocket(wsUrl);
      websocketConnection.addEventListener("message", onServerMessage);
      //websocketConnection.onopen = function(event) { websocketConnection.send("Hoi!"); };
      console.log("Capture setup complete.");
    } );
  }
}

window.onload = function() {
  // stream is the incoming front stream
  frontoutput = document.getElementById("frontoutput");
  // stream2 is the incoming surface stream
  surfaceoutput = document.getElementById("surfaceoutput");
  // "canvas"/context is the primary, visible drawing surface
  canvas = document.getElementById("surfacecanvas");
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
  canvas.ontouchmove = onCanvasMove;

  canvas.addEventListener("contextmenu", function(e) { e.preventDefault(); } );
  var config = { 'iceServers': [{urls:"stun:stun.l.google.com:19302"},{urls:"stun:stun.ekiga.net"}] };
  playStream(config, function (errmsg) { console.error(errmsg); });
  colors = ["red", "cyan", "yellow", "blue", "magenta" ];
  mycolor = colors[Math.floor(Math.random() * colors.length)];
  context.strokeStyle = mycolor; context.fillStyle = mycolor; context.fillRect(10, 10, 20, 20);

  // canvas2/c2 is the surface stream source (invisible drawing surface with green background)
  surfacesource = document.getElementById("surfacesource");
  c2 = surfacesource.getContext("2d");
  surfacesource.width=1280;
  surfacesource.height=720;

  // canvas3/c3 is for the virtual avatar front stream in VR
  frontsource = document.getElementById("frontsource");
  if (frontsource) {
  c3 = frontsource.getContext("webgl");
  frontsource.width=640;
  frontsource.height=360;
  }

  c2.fillStyle = "rgba(0,255,0,255)";
  c2.fillRect(0, 0, surfacesource.width, surfacesource.height);

  // "stream3"/video3 is for the local desktop capture stream
  desktopsource = document.getElementById("desktopsource");
  startbtn = document.getElementById("start");

  if (startbtn) startbtn.addEventListener("click", function(e) {
    let captureopts = { video: { width: 1280 }, audio: false, surfaceSwitching: "include", selfBrowserSurface: "exclude" };
    navigator.mediaDevices.getDisplayMedia(captureopts).then( (stream) => {
      console.log(stream);
      windowstream = stream.getVideoTracks()[0];
      desktopsource.srcObject = stream;
      desktopsource.play().catch(reportError);
      drawVideo();
    } );
  } );
  setTimeout( () => { requestAnimationFrame(drawStickers); }, 2000 );
};
