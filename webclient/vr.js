var audioCtx;
var analyser;
var source;

function vr_init() {
  vr_fakefront_init();
}

function vr_fakefront_init() {
  // canvas3/c3 is for the virtual avatar front stream in VR
  frontsource = document.getElementById("frontsource");
  if (frontsource) {
    c3 = frontsource.getContext("webgl");
    frontsource.width=1280;
    frontsource.height=720;
  }
}

function vr_audio_init(mediastream) {
  // from https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Visualizations_with_Web_Audio_API
  audioCtx = new AudioContext();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  source = audioCtx.createMediaStreamSource(mediastream);
  source.connect(analyser);
  setTimeout(updateAudioFeedback,50);
}

function updateAudioFeedback() {

  var target = document.getElementById("mouth");
  if (target === null) return;
  
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyser.getByteFrequencyData(dataArray);
  
  scale = (dataArray[1] / 255.0) + (dataArray[2] / 255.0);
  
  target.object3D.scale.set(scale, scale, scale);
  setTimeout(updateAudioFeedback, 50);
}
  