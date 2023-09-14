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

let offset = [0, 0];
let isDragging = false;
var touchTimer;
let isResizing = false;

function add_sticker(elem) {
    let isConfirm = false;
  
    var sticker = document.createElement('div');
    sticker.className = 'new_sticker';
    sticker.addEventListener("touchstart", function(e) {
      isDragging = true;
      offset = [
        sticker.offsetLeft - e.touches[0].clientX,
        sticker.offsetTop - e.touches[0].clientY
      ];
      
      if (e.touches.length === 2) {
        isResizing = true;
        startDistance = getDistanceBetweenTouches(e.touches);
        startAngle    = getAngleBetweenTouches(e.touches);
        curAngle = 0;
        if (sticker.style.transform) curAngle = Number(sticker.style.transform.split("(")[1].split("d")[0]);
        console.log(curAngle);
        startScale = sticker_scale;
      }
      sticker.parentNode.appendChild(sticker);
    });  
    
    sticker.addEventListener("touchend", function() {
      isDragging = false;
      isResizing = false;
    });

    sticker.addEventListener("touchmove", function(e) {
      e.preventDefault();
      if (isDragging && isConfirm == false) {
        sticker.style.left = (e.touches[0].clientX + offset[0]) + 'px';
        sticker.style.top  = (e.touches[0].clientY + offset[1]) + 'px';
        //console.log("offset:"+offset);
      }
      
      if (isResizing) {
        /*var currentDistance = getDistanceBetweenTouches(e.touches);
        var newScale = startScale * (currentDistance / startDistance);
        setStickerScale(newScale);*/
        var currentAngle = getAngleBetweenTouches(e.touches);
        var deltaAngle = startAngle - currentAngle;
        console.log(currentAngle,deltaAngle,curAngle);
        setStickerRotation(curAngle+deltaAngle);
      }
    });
  
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

    function setStickerScale(scale) {
      sticker_scale = scale;
      sticker_img.style.transform = "scale(" + scale + ")";
      //var rotation = getRotationDegrees(sticker_img);
      //sticker_img.style.transform = "scale(" + scale + ") rotate(" + rotation + "deg)";

      sticker.style.width = (sticker_img.clientWidth * scale) + 'px';
      sticker.style.height = (sticker_img.clientHeight * scale) + 'px';
    }

    function setStickerRotation(rotation) {
      var tmp = "rotate(" + rotation + "deg)";
      sticker.style.transform = tmp;
      //var rotation = getRotationDegrees(sticker_img);
      //sticker_img.style.transform = "scale(" + scale + ") rotate(" + rotation + "deg)";
    }

    var sticker_img = document.createElement('img');
    sticker_img.src = $(elem).prop('src');
    var sticker_scale = 1;
    sticker.appendChild(sticker_img);
    $('#fakecanvas').append(sticker);
    //drawStickers();
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
    var transform2 = sticker.firstChild.style.transform;
    var angle = 0;
    var scale = 1;
    if (transform1 && transform1.includes("rotate")) angle = transform1.split("(")[1].split("d")[0];
    if (transform2 && transform2.includes("scale"))  scale = transform2.split("(")[1].split(")")[0];
    var scalex = surfacesource.width  / surfacesource.offsetWidth;
    var scaley = surfacesource.height / surfacesource.offsetHeight;
    var x = sticker.offsetLeft * (1280 / surfacesource.offsetWidth );
    var y = sticker.offsetTop  * ( 720 / surfacesource.offsetHeight);
    myDrawImage(sourcectx,sticker.firstChild,x,y,angle,scale*scalex);
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
