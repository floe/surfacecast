var background = "";

$('#clearAll_btn').on("click", function() {
    $("#fakecanvas").empty();
    canvasctx.globalCompositeOperation = "destination-out";
    canvasctx.fillStyle = "rgba(0,0,0,255)";
    canvasctx.fillRect(0, 0, canvas.width, canvas.height);
});

function changeBg(btn){
    let id = "#" + btn.id;
    let url = $(id).css("background-image");
    //$('#fakecanvas').css("background-image", url);
    //$('#fakecanvas').css("background-size", "cover");
    url = url.split("/");
    background = document.createElement("img");
    background.src = url[3]+"/"+url[4].split("\"")[0];
}

function defaultBg(){
    //$('#fakecanvas').css("background", "none");
    background=null;
    bgBtnDeactive();
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
  console.log(evt);
}

function move_start(evt) {
  touchify(evt);
  var sticker = evt.target;
  evt.preventDefault();

  sticker.isDragging = true;
  sticker.offset = [
    sticker.offsetLeft - evt.touches[0].clientX,
    sticker.offsetTop - evt.touches[0].clientY
  ];

  if (evt.touches.length === 2) {
    sticker.isResizing = true;
    sticker.startDistance = getDistanceBetweenTouches(e.touches);
    sticker.startAngle = getAngleBetweenTouches(e.touches);
    sticker.curAngle = 0;
    if (sticker.style.transform) sticker.curAngle = Number(sticker.style.transform.split("(")[1].split("d")[0]);
  }
  sticker.parentNode.appendChild(sticker);
}

function move_end(evt) {
  var sticker = evt.target;
  sticker.isDragging = false;
  sticker.isResizing = false;
}

function do_move(evt) {
  touchify(evt);
  var sticker = evt.target;
  if (!sticker.isDragging) return;
  evt.preventDefault();

  if (sticker.isDragging) {
    sticker.style.left = (evt.touches[0].clientX + sticker.offset[0]) + 'px';
    sticker.style.top = (evt.touches[0].clientY + sticker.offset[1]) + 'px';
    console.log("offset:"+sticker.offset);
  }

  if (sticker.isResizing) {
    /*var currentDistance = getDistanceBetweenTouches(e.touches);
    var newScale = startScale * (currentDistance / startDistance);
    setStickerScale(newScale);*/
    var currentAngle = getAngleBetweenTouches(e.touches);
    var deltaAngle = sticker.startAngle - currentAngle;
    console.log(currentAngle, deltaAngle, curAngle);
    setStickerRotation(sticker, curAngle + deltaAngle);
  }
}

function setStickerScale(sticker,scale) {
  var sticker_img = sticker.firstChild;
  sticker_img.style.transform = "scale(" + scale + ")";
  sticker.style.width = (sticker_img.clientWidth * scale) + 'px';
  sticker.style.height = (sticker_img.clientHeight * scale) + 'px';
}

function setStickerRotation(sticker,rotation) {
  var tmp = "rotate(" + rotation + "deg)";
  sticker.style.transform = tmp;
}

function add_sticker(elem) {
  
    var sticker = document.createElement("img");
    sticker.className = "sticker";

    sticker.addEventListener("touchstart", move_start);  
    sticker.addEventListener("mousedown",  move_start);  
    sticker.addEventListener("touchend",   move_end);
    sticker.addEventListener("mouseup",    move_end);
    sticker.addEventListener("touchmove",  do_move);
    sticker.addEventListener("mousemove",  do_move);

    sticker.src = elem[0].src;
    $('#fakecanvas').append(sticker);
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
  var fc = $('#fakecanvas')[0];
  var stickers = fc.childNodes;
  if (background) {
    myDrawImage(sourcectx,background,0,0);
  } else {
    sourcectx.fillStyle = "rgba(0,255,0,255)";
    sourcectx.fillRect(0, 0, surfacesource.width, surfacesource.height);
  }
  for (const sticker of stickers) {
    //console.log(sticker.firstChild,sticker.firstChild.style.transform,sticker.offsetLeft,sticker.offsetTop);
    var transform1 = sticker.style.transform;
    var transform2 = sticker.style.transform; // FIXME: should be sticker.firstChild (i.e. the image)
    var angle = 0;
    var scale = 1;
    if (transform1 && transform1.includes("rotate")) angle = transform1.split("(")[1].split("d")[0];
    if (transform2 && transform2.includes("scale"))  scale = transform2.split("(")[1].split(")")[0];
    var scalex = surfacesource.width  / surfacesource.offsetWidth;
    var scaley = surfacesource.height / surfacesource.offsetHeight;
    var x = sticker.offsetLeft * (1280 / surfacesource.offsetWidth );
    var y = sticker.offsetTop  * ( 720 / surfacesource.offsetHeight);
    myDrawImage(sourcectx,sticker,x,y,angle,scale*scalex);
    //console.log("fc:"+fc.offsetWidth+" "+fc.offsetHeight);
    //console.log("sticker:"+sticker.offsetLeft+" "+sticker.offsetTop);
    //console.log("sx sy:"+scalex+" "+scaley);
  }
  sourcectx.drawImage( canvas,0,0 );
  // 15 FPS rate-limiting, cf. https://stackoverflow.com/q/19764018
  setTimeout( () => { requestAnimationFrame(drawStickers); }, 1000/15 );
}

add_sticker($("#t1"));
add_sticker($("#t2"));
add_sticker($("#t3"));
add_sticker($("#t4"));
add_sticker($("#t5"));
add_sticker($("#t6"));
add_sticker($("#t7"));

$("#stream").on("click", function(){document.documentElement.requestFullscreen();});
