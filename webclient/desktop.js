var desktopsource;

function drawVideo() {
    c2.drawImage( desktopsource, 0, 0, 1280, 720 );
    c2.drawImage( canvas, 0, 0, 1280, 720 );
    // 15 FPS rate-limiting, cf. https://stackoverflow.com/q/19764018
    setTimeout( () => { requestAnimationFrame(drawVideo); }, 1000/15 );
  }
  
function desktop_init() {
  // "stream3"/video3 is for the local desktop capture stream
  desktopsource = document.getElementById("desktopsource");
  startbtn = document.getElementById("start");

  if (startbtn) startbtn.addEventListener("click", function(e) {
    let captureopts = { video: { width: 1280 }, audio: false, surfaceSwitching: "include", selfBrowserSurface: "exclude" };
    navigator.mediaDevices.getDisplayMedia(captureopts).then( (stream) => {
      console.log(stream);
      //windowstream = stream.getVideoTracks()[0];
      desktopsource.srcObject = stream;
      desktopsource.play().catch(reportError);
      drawVideo();
    } );
  } );
}