var html5VideoElement;
var html5VideoElement2;
var websocketConnection;
var webrtcPeerConnection;
var webrtcConfiguration;
var reportError;
var datastream;
var canvas;
var context;



// adapted from: https://www.npmjs.com/package/intrinsic-scale
function getObjectFitSize(
  contains /* true = contain, false = cover */,
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
}


function onCanvasClick(evt) {
  const rect = canvas.getBoundingClientRect()
  const centerX = evt.clientX - rect.left; //canvas.width / 2;
  const centerY = evt.clientY - rect.top;  //canvas.height / 2;
  const radius = 5;
  console.log("click"+centerX+" "+centerY);

  context.beginPath();
  context.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
  context.fillStyle = "red";
  context.fill();
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
  html5VideoElement.srcObject = event.streams[0];
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

function onvideoplay(event) {
  var stream1 = html5VideoElement.srcObject;
  var vtracks = stream1.getVideoTracks();
  if (vtracks.length < 2) { return; }
  html5VideoElement.srcObject.removeTrack( vtracks[1] );
  var stream2 = new MediaStream( [ vtracks[1] ] );
  html5VideoElement2.srcObject = stream2;
  html5VideoElement2.play();
  // FIXME: on Chrome, canvas stream only starts after first onclick event?
  context.fillStyle = "rgba(0,255,0,0)";
  context.fillRect(0, 0, canvas.width, canvas.height);
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

      webrtcPeerConnection.addStream(stream);
      webrtcPeerConnection.addStream(canvas.captureStream(15));

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
  fixCanvas(canvas);
  canvas.onclick = onCanvasClick;
  context = canvas.getContext("2d");
  var config = { 'iceServers': [] };
  playStream(vidstream, null, null, null, config, function (errmsg) { console.error(errmsg); });
  vidstream.onplay = onvideoplay;
};
