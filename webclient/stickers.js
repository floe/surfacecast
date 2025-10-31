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

function getDistanceBetweenPointers(pointers) {
  var pointer1 = pointers[0];
  var pointer2 = pointers[1];
  var dx = pointer1.clientX - pointer2.clientX;
  var dy = pointer1.clientY - pointer2.clientY;
  return Math.sqrt(dx*dx + dy*dy);
}

function getAngleBetweenPointers(pointers) {
  var pointer1 = pointers[0];
  var pointer2 = pointers[1];
  var dx = pointer1.clientX - pointer2.clientX;
  var dy = pointer1.clientY - pointer2.clientY;
  return -360*Math.atan2(dy,dx)/(2*Math.PI);
}

function move_start(evt) {
  var sticker = evt.target;
  evt.preventDefault();

  // erase sticker on right click or if eraser is active
  if (evt.buttons > 1 || paintmode == 2 ) {
    sticker.remove();
    return;
  }

  // Initialize pointers array if it doesn't exist
  if (!sticker.activePointers) {
    sticker.activePointers = [];
  }

  // Add this pointer to the active pointers
  sticker.activePointers.push({
    pointerId: evt.pointerId,
    clientX: evt.clientX,
    clientY: evt.clientY
  });

  sticker.isActive = true;
  
  // Set pointer capture for better tracking
  try { sticker.setPointerCapture(evt.pointerId); } catch(e) {}

  if (sticker.activePointers.length === 1) {
    // Single pointer - setup for dragging
    sticker.offset = [
      sticker.offsetLeft - evt.clientX,
      sticker.offsetTop - evt.clientY
    ];
  } else if (sticker.activePointers.length >= 2) {
    // Multiple pointers - setup for pinch/rotate
    sticker.startDistance = getDistanceBetweenPointers(sticker.activePointers);
    sticker.startAngle = getAngleBetweenPointers(sticker.activePointers);
  }

  // move sticker to the top
  sticker.parentNode.appendChild(sticker);
}

function move_end(evt) {
  var sticker = evt.target;
  
  // Release pointer capture
  try { sticker.releasePointerCapture(evt.pointerId); } catch(e) {}

  // Remove this pointer from active pointers
  if (sticker.activePointers) {
    sticker.activePointers = sticker.activePointers.filter(p => p.pointerId !== evt.pointerId);
    
    // If we still have 2 or more pointers, recalculate start values for remaining pointers
    if (sticker.activePointers.length >= 2) {
      sticker.startDistance = getDistanceBetweenPointers(sticker.activePointers);
      sticker.startAngle = getAngleBetweenPointers(sticker.activePointers);
    }
    
    // If no more pointers, deactivate
    if (sticker.activePointers.length === 0) {
      sticker.isActive = false;
    }
  } else {
    sticker.isActive = false;
  }
}

function wheel(evt) {
  evt.preventDefault();
  var delta = evt.deltaY < 0 ? -5 : 5;
  var sticker = evt.target;
  if (evt.shiftKey) setStickerScale(sticker,sticker.curScale+(0.01*delta));
  else setStickerRotation(sticker,sticker.curAngle+delta);
}

function do_move(evt) {
  var sticker = evt.target;
  if (!sticker.isActive) return;
  evt.preventDefault();

  // Update the position of this pointer in the activePointers array
  if (sticker.activePointers) {
    var pointerIndex = sticker.activePointers.findIndex(p => p.pointerId === evt.pointerId);
    if (pointerIndex !== -1) {
      sticker.activePointers[pointerIndex].clientX = evt.clientX;
      sticker.activePointers[pointerIndex].clientY = evt.clientY;
    } else {
      // Pointer not found - possibly a race condition, ignore this event
      return;
    }
  }

  if (sticker.activePointers && sticker.activePointers.length >= 2) {
    // Multi-pointer gesture: scale and rotate
    var currentDistance = getDistanceBetweenPointers(sticker.activePointers);
    
    // Prevent division by zero if pointers start at the same position
    if (sticker.startDistance === 0 || currentDistance === 0) return;
    
    var newScale = currentDistance / sticker.startDistance;
    sticker.startDistance = currentDistance;
    setStickerScale(sticker, sticker.curScale * newScale);

    var currentAngle = getAngleBetweenPointers(sticker.activePointers);
    var deltaAngle = sticker.startAngle - currentAngle;
    sticker.startAngle = currentAngle;
    setStickerRotation(sticker, sticker.curAngle + deltaAngle);
  } else {
    // Single pointer: drag
    sticker.style.left = (evt.clientX + sticker.offset[0]) + 'px';
    sticker.style.top  = (evt.clientY + sticker.offset[1]) + 'px';
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

    sticker.addEventListener("pointerdown", move_start);
    sticker.addEventListener("pointerup",   move_end);
    sticker.addEventListener("pointermove", do_move);
    sticker.addEventListener("pointercancel", move_end); // Handle pointer cancel (e.g., when pointer is lost)
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