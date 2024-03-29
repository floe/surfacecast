var background = null;
var fakecanvas = null;

function clear_all() {
    fakecanvas.replaceChildren();
    background = null;
    canvasctx.globalCompositeOperation = "destination-out";
    canvasctx.fillStyle = "rgba(0,0,0,255)";
    canvasctx.fillRect(0, 0, canvas.width, canvas.height);
};

function backgroundFunc(that) {
  var files = that.files;
  background = document.createElement("img");
  background.src = URL.createObjectURL(files[0]);
}

// courtesy of https://stackoverflow.com/a/75045656/
function imagePreviewFunc(that, previewerId) {
  var files = that.files;
  for (var i = 0; i < files.length; i++) {
    var image = document.createElement("img");
    image.src = URL.createObjectURL(files[i]);
    image.classList.add("rotate","scale");
    image.onclick = add_sticker;
    document.getElementById(previewerId).append(image);
  }
}

function getDistanceBetweenTouches(touches) {
  var touch1 = touches[0];
  var touch2 = touches[1];
  var dx = touch1.clientX - touch2.clientX;
  var dy = touch1.clientY - touch2.clientY;
  return Math.sqrt(dx*dx + dy*dy);
}

function getAngleBetweenTouches(touches) {
  var touch1 = touches[0];
  var touch2 = touches[1];
  var dx = touch1.clientX - touch2.clientX;
  var dy = touch1.clientY - touch2.clientY;
  return -360*Math.atan2(dy,dx)/(2*Math.PI);
}

function touchify(evt) {
  if (evt.touches === undefined) {
    evt.touches = [ { clientX: evt.clientX, clientY: evt.clientY } ];
  }
  //console.log(evt);
}

function move_start(evt) {
  touchify(evt);
  var sticker = evt.target;
  evt.preventDefault();

  // erase sticker on right click or if eraser is active
  if (evt.buttons > 1 || paintmode == 2 ) {
    sticker.remove();
    return;
  }

  sticker.isActive = true;
  sticker.offset = [
    sticker.offsetLeft - evt.touches[0].clientX,
    sticker.offsetTop - evt.touches[0].clientY
  ];

  if (evt.touches.length >= 2) {
    sticker.startDistance = getDistanceBetweenTouches(evt.touches);
    sticker.startAngle = getAngleBetweenTouches(evt.touches);
  }

  // move sticker to the top
  sticker.parentNode.appendChild(sticker);
}

function move_end(evt) {
  var sticker = evt.target;
  sticker.isActive = false;
}

function wheel(evt) {
  evt.preventDefault();
  var delta = evt.deltaY < 0 ? -5 : 5;
  var sticker = evt.target;
  if (evt.shiftKey) setStickerScale(sticker,sticker.curScale+(0.01*delta));
  else setStickerRotation(sticker,sticker.curAngle+delta);
}

function do_move(evt) {
  touchify(evt);
  var sticker = evt.target;
  if (!sticker.isActive) return;
  evt.preventDefault();

  sticker.style.left = (evt.touches[0].clientX + sticker.offset[0]) + 'px';
  sticker.style.top  = (evt.touches[0].clientY + sticker.offset[1]) + 'px';

  if (evt.touches.length >= 2) {
    var currentDistance = getDistanceBetweenTouches(evt.touches);
    var newScale = currentDistance / sticker.startDistance;
    sticker.startDistance = currentDistance;
    setStickerScale(sticker, sticker.curScale * newScale);

    var currentAngle = getAngleBetweenTouches(evt.touches);
    var deltaAngle = sticker.startAngle - currentAngle;
    sticker.startAngle = currentAngle;
    setStickerRotation(sticker, sticker.curAngle + deltaAngle);
  }
}

function setStickerScale(sticker,scale) {
  if (!sticker.classList.contains("scale")) return;
  sticker.curScale = scale;
  setStickerTransform(sticker);
}

function setStickerRotation(sticker,rotation) {
  if (!sticker.classList.contains("rotate")) return;
  sticker.curAngle = rotation;
  setStickerTransform(sticker);
}

function setStickerTransform(sticker) {
  sticker.style.transform = "scale(" + sticker.curScale + ") translate(50%, 50%) rotate(" + sticker.curAngle + "deg) translate(-50%, -50%)"; // scale(" + sticker.curScale + ")";
}

function add_sticker(elem) {
  
    // if called via event, replace event with its own target
    if (elem.classList === undefined) elem = elem.target;

    var sticker = document.createElement("img");
    sticker.className = "sticker";

    sticker.curAngle = 0;
    sticker.curScale = 1;

    sticker.addEventListener("touchstart", move_start);  
    sticker.addEventListener("mousedown",  move_start);  
    sticker.addEventListener("touchend",   move_end);
    sticker.addEventListener("mouseup",    move_end);
    sticker.addEventListener("touchmove",  do_move);
    sticker.addEventListener("mousemove",  do_move);
    sticker.addEventListener("wheel",      wheel);

    sticker.src = elem.src;
    for (const cl of elem.classList) sticker.classList.add(cl);
    fakecanvas.append(sticker);

    // set intial scale for all stickers based on canvas width
    sticker.curScale = fakecanvas.offsetWidth / 1280.0;
    setStickerTransform(sticker);
}

// courtesy of https://gist.github.com/Luftare/fd238b7aac27c4e82c13b4a9526c878f
function myDrawImage(ctx, img, x, y, angle = 0, scale = 1) {
  ctx.save();
  ctx.translate(x + img.width * scale / 2, y + img.height * scale / 2);
  ctx.rotate(2 * Math.PI * angle/360.0);
  ctx.translate(- x - img.width * scale / 2, - y - img.height * scale / 2);
  ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
  ctx.restore();
}

// TODO: animations
function drawStickers() {
  var stickers = fakecanvas.childNodes;
  if (background) {
    myDrawImage(sourcectx,background,0,0);
  } else {
    sourcectx.fillStyle = "rgba(0,255,0,255)";
    sourcectx.fillRect(0, 0, surfacesource.width, surfacesource.height);
  }
  var scalex = surfacesource.width  / surfacesource.offsetWidth;
  var scaley = surfacesource.height / surfacesource.offsetHeight;
  for (const sticker of stickers) {
    var x = sticker.offsetLeft * scalex;
    var y = sticker.offsetTop  * scaley;
    myDrawImage(sourcectx,sticker,x,y,sticker.curAngle,sticker.curScale*scalex);
  }
  sourcectx.drawImage( canvas,0,0 );
  // 15 FPS rate-limiting, cf. https://stackoverflow.com/q/19764018
  setTimeout( () => { requestAnimationFrame(drawStickers); }, 1000/15 );
}

function stickers_init() {
  fakecanvas = document.getElementById("fakecanvas");
  drawStickers();
}