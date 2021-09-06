var html5VideoElement;
var html5VideoElement2;
var websocketConnection;
var webrtcPeerConnection;
var webrtcConfiguration;
var reportError;
var datastream;
var canvas;
var context;
var canvasstream;
var mousedown;
var mycolor;
var x,y;


// adapted from: https://www.npmjs.com/package/intrinsic-scale
/*function getObjectFitSize(
  contains, // true = contain, false = cover
  containerWidth,
  containerHeight,
  width,
  height
) {
  var doRatio = width / height;
  var cRatio = containerWidth / containerHeight;
  var targetWidth = 0;
  var targetHeight = 0;
  var test = contains ? doRatio > cRatio : doRatio < cRatio;

  if (test) {
    targetWidth = containerWidth;
    targetHeight = targetWidth / doRatio;
  } else {
    targetHeight = containerHeight;
    targetWidth = targetHeight * doRatio;
  }

  return {
    width: targetWidth,
    height: targetHeight,
    x: (containerWidth - targetWidth) / 2,
    y: (containerHeight - targetHeight) / 2
  };
}

function fixCanvas(myCanvas) {

  const dimensions = getObjectFitSize(
    true,
    myCanvas.clientWidth,
    myCanvas.clientHeight,
    myCanvas.width,
    myCanvas.height
  );

  myCanvas.width = dimensions.width;
  myCanvas.height = dimensions.height;
}*/


function onCanvasDown(evt) { x = evt.offsetX; y = evt.offsetY; mousedown = evt.buttons; }
function onCanvasUp  (evt) { onCanvasMove(evt);                mousedown = 0; }
function onCanvasMove(evt) {
  if (mousedown == 0) return;
  const centerX = evt.offsetX;
  const centerY = evt.offsetY;
  const radius = (mousedown == 1) ? 5 : 20;

  context.beginPath();
  context.lineWidth = radius;
  context.strokeStyle = (mousedown == 1) ? mycolor : "rgba(0,255,0,1)";
  context.fillStyle = context.strokeStyle
  context.globalCompositeOperation = (mousedown == 1) ? "source-over" : "destination-out";
  //context.strokeStyle = mycolor;
  context.moveTo(x,y);
  context.lineTo(centerX,centerY);
  context.stroke();
  context.arc(centerX, centerY, radius/2, 0, 2 * Math.PI, false);
  context.fill();
  context.closePath();

  x = centerX;
  y = centerY;
}


function onLocalDescription(desc) {
  console.log("Local description: " + JSON.stringify(desc));
  webrtcPeerConnection.setLocalDescription(desc).then(function() {
    websocketConnection.send(JSON.stringify({ "type": "sdp", "data": webrtcPeerConnection.localDescription }));
  }).catch(reportError);
}


function onIncomingSDP(sdp) {
  console.log("Incoming SDP: " + JSON.stringify(sdp));
  webrtcPeerConnection.setRemoteDescription(sdp).catch(reportError);
  webrtcPeerConnection.createAnswer().then(onLocalDescription).catch(reportError);
}


function onIncomingICE(ice) {
  var candidate = new RTCIceCandidate(ice);
  console.log("Incoming ICE: " + JSON.stringify(ice));
  webrtcPeerConnection.addIceCandidate(candidate).catch(reportError);
}


function onAddRemoteStream(event) {
  //console.log(event.streams[0].getVideoTracks());
  //console.log(event.streams[0].getAudioTracks());
  // FIXME: is this enough to fix Safari?
  var stream1 = event.streams[0];
  var vtracks = stream1.getVideoTracks();
  if (vtracks.length < 2) { return; }
  html5VideoElement.srcObject = event.streams[0];
  html5VideoElement.srcObject.removeTrack( vtracks[1] );
  var stream2 = new MediaStream( [ vtracks[1] ] );
  html5VideoElement2.srcObject = stream2;
  html5VideoElement2.play();
  // FIXME: on Chrome, canvas stream only starts after first onclick event?
  context.fillStyle = "rgba(0,255,0,0)";
  context.fillRect(0, 0, canvas.width, canvas.height);
}


function onIceCandidate(event) {
  if (event.candidate == null)
    return;

  console.log("Sending ICE candidate out: " + JSON.stringify(event.candidate));
  websocketConnection.send(JSON.stringify({ "type": "ice", "data": event.candidate }));
}

function getLocalStreams() {
  var constraints = {video: { width: 640, height: 360, facingMode: "user" }, audio: true};
  return navigator.mediaDevices.getUserMedia(constraints);
}


function onServerMessage(event) {
  var msg;

  try {
    msg = JSON.parse(event.data);
  } catch (e) {
    return;
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

  if (!webrtcPeerConnection) {
    getLocalStreams().then( (stream) => {
      
      webrtcPeerConnection = new RTCPeerConnection(webrtcConfiguration);
      webrtcPeerConnection.ontrack = onAddRemoteStream;
      webrtcPeerConnection.onicecandidate = onIceCandidate;

      datastream = webrtcPeerConnection.createDataChannel("events");
      datastream.onopen = function(event) { datastream.send("Hi!"); console.log("Hi!"); }
      // datastream.onmessage = ...

      for (const track of stream.getTracks()) { webrtcPeerConnection.addTrack(track, stream); }

    context.beginPath();
    context.arc(0, 0, 5, 0, 2 * Math.PI, false);
    context.fillStyle = "yellow";
    context.fill();

      canvasstream = canvas.captureStream(15);
      canvastrack = canvasstream.getVideoTracks()[0];
      //canvastrack.requestFrame();
      canvastrack.contentHint = "detail";
      for (const track of canvasstream.getTracks()) { webrtcPeerConnection.addTrack(track, stream); }

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
  canvas.onmousedown = onCanvasDown;
  canvas.onmouseup   = onCanvasUp;
  canvas.onmousemove = onCanvasMove;
  var config = { 'iceServers': [{urls:"stun:stun.l.google.com:19302"},{urls:"stun:stun.ekiga.net"}] };
  playStream(vidstream, null, null, null, config, function (errmsg) { console.error(errmsg); });
  colors = ["red", "cyan", "yellow", "blue", "magenta" ];
  mycolor = colors[Math.floor(Math.random() * colors.length)];
};
