let bgSubmenuIsOpen = false;
let effectSubmenuIsOpen = false;
let brushMenuIsOpen = false;
var background = "";

$('#clearAll_btn').on("click", function() {
    $("#fakecanvas").empty();
    context.globalCompositeOperation = "destination-out";
    context.fillStyle = "rgba(0,0,0,255)";
    context.fillRect(0, 0, canvas.width, canvas.height);
});

$('#brush_btn').on("click", function() {
  if (brushMenuIsOpen) {
    brushBtnDeactive();
  } else {
    bgBtnDeactive();
    effectBtnDeactive();
    brushBtnActive();
  }
});

$('#bg_btn').on("click", function() {
    bgBtnActive();
    effectBtnDeactive();
    brushBtnDeactive();
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

$('#effect_btn').on("click", function() {
    effectBtnActive();  
    bgBtnDeactive();
    brushBtnDeactive();
    stickModeOn = false;
});

let sidebarIsOpen = false;
let stickModeOn = false;

$('#stickers_btn').on("click", function() {
  if(sidebarIsOpen==false)  {
    openSidebar();
  } else {
    closeSidebar();
  }
});

function openSidebar(){
  $('#side_panel').css({width: "450px" });
  $('#side_panel').css({padding: "0px 0px 0px 42px" });
  $('#stickers_btn').css({right: "442px" });
  $('#stickers_btn').css({transform: "rotate(180deg)"});
  $('#stickers_btn').css({background: "white" });
  sidebarIsOpen = true;
  stickModeOn = true;
  bgBtnDeactive();
  effectBtnDeactive();
}

function closeSidebar(){
  $('#side_panel').css({width: "0px" });
  $('#side_panel').css({padding: "0px" });
  $('#stickers_btn').css({right: "0px" });
  $('#stickers_btn').css({transform: "rotate(360deg)"});
  $('#stickers_btn').css({background: "rgba(230, 230, 230, 0.7)" });
  sidebarIsOpen = false;
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
        var newAngle = startAngle - currentAngle;
        setStickerRotation(newAngle);
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
      return Math.atan(dy/dx);
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
      var tmp = "rotate(" + -360*rotation/(2*Math.PI) + "deg)";
      sticker.style.transform = tmp;
      //var rotation = getRotationDegrees(sticker_img);
      //sticker_img.style.transform = "scale(" + scale + ") rotate(" + rotation + "deg)";
    }

    /*sticker.ondblclick = function() {
      //this.style.border = "1px solid grey";
      this.querySelector('.delete_sticker_btn').style.visibility = "visible";
      this.querySelector('.confirm_sticker_btn').style.visibility = "visible";
      this.querySelector('.rotate_sticker_btn').style.visibility = "visible";
      
      isConfirm = false;
    }*/
  
    var sticker_img = document.createElement('img');
    sticker_img.src = $(elem).prop('src');
    var sticker_scale = 1;
      
    
    /*var confirm_btn = document.createElement('button');
    confirm_btn.className = 'confirm_sticker_btn';
    confirm_btn.innerHTML = '<svg width=\'22\' height=\'22\' viewBox=\'0 0 22 22\'fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'><path d=\'M1 11.4762L7.4 21L21 1\' stroke=\'green\' stroke-width=\'2\' stroke-linecap=\'round\'stroke-linejoin=\'round\'></svg>';
    confirm_btn.onclick = function(){
      isConfirm = true;
      this.style.visibility = "hidden";
      this.parentElement.querySelector('.delete_sticker_btn').style.visibility = "hidden";
      this.parentElement.querySelector('.rotate_sticker_btn').style.visibility = "hidden";
      this.parentElement.style.border = "0px solid grey";
    };
  
    /*var delete_btn = document.createElement('button');
    delete_btn.className = 'delete_sticker_btn';
    delete_btn.innerHTML = '<svg width=\'22\' height=\'22\' viewBox=\'0 0 22 22\'fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'><path d=\'M1 1L21 21M1 21L21 1\' stroke=\'black\' stroke-width=\'2\' stroke-linecap=\'round\'stroke-linejoin=\'round\'></svg>';
    delete_btn.onclick = function(){
      this.parentElement.remove();
    };
  
    var rotate_btn = document.createElement('button');
    rotate_btn.className = 'rotate_sticker_btn';
    rotate_btn.innerHTML = '<svg width=\'28\' height=\'28\' viewBox=\'0 0 43 39\' fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'><path d=\'M42.3242 19.4986C42.3247 24.6256 40.3182 29.5466 36.739 33.1963C33.1598 36.8461 28.2959 38.9311 23.2001 39H22.9396C17.9889 39.0124 13.2236 37.1065 9.63287 33.6777C9.47868 33.531 9.35472 33.3552 9.26807 33.1603C9.18142 32.9653 9.13379 32.7552 9.12788 32.5417C9.12197 32.3283 9.15791 32.1158 9.23365 31.9163C9.30938 31.7168 9.42342 31.5343 9.56927 31.3792C9.71511 31.2241 9.8899 31.0994 10.0836 31.0122C10.2774 30.925 10.4863 30.8771 10.6985 30.8712C10.9106 30.8652 11.1219 30.9014 11.3201 30.9776C11.5184 31.0538 11.6998 31.1685 11.854 31.3152C14.1636 33.5065 17.0638 34.9645 20.1923 35.5072C23.3208 36.0499 26.5389 35.6531 29.4445 34.3666C32.3502 33.08 34.8146 30.9606 36.53 28.2732C38.2453 25.5857 39.1355 22.4494 39.0893 19.2559C39.0431 16.0625 38.0626 12.9535 36.2703 10.3174C34.478 7.68131 31.9533 5.63494 29.0116 4.43395C26.07 3.23296 22.8418 2.93059 19.7303 3.56461C16.6189 4.19863 13.7621 5.74093 11.5168 7.99885C11.5003 8.0168 11.4828 8.03376 11.4643 8.04963L6.0972 12.9981H11.6319C12.0603 12.9981 12.4712 13.1693 12.7742 13.4741C13.0771 13.7789 13.2473 14.1922 13.2473 14.6232C13.2473 15.0542 13.0771 15.4676 12.7742 15.7724C12.4712 16.0771 12.0603 16.2484 11.6319 16.2484H1.9396C1.51118 16.2484 1.1003 16.0771 0.797354 15.7724C0.49441 15.4676 0.324219 15.0542 0.324219 14.6232V4.87253C0.324219 4.44152 0.49441 4.02817 0.797354 3.7234C1.1003 3.41863 1.51118 3.24741 1.9396 3.24741C2.36803 3.24741 2.77891 3.41863 3.08185 3.7234C3.3848 4.02817 3.55499 4.44152 3.55499 4.87253V10.9261L9.25931 5.68509C11.9731 2.96554 15.427 1.1158 19.1849 0.369391C22.9428 -0.377019 26.8363 0.0133586 30.3739 1.49124C33.9114 2.96913 36.9345 5.46826 39.0614 8.67317C41.1883 11.8781 42.3237 15.6451 42.3242 19.4986Z\' fill=\'#515151\'/></svg>';
    let currentRotation = 0;
    rotate_btn.onclick = function(){
      currentRotation = (currentRotation + 90) % 360;
      sticker.style.transform = 'rotate(' + currentRotation + 'deg)';
    };*/

    sticker.appendChild(sticker_img);
    /*sticker.appendChild(delete_btn);
    sticker.appendChild(confirm_btn);
    if(elem.className == "rotatable"){sticker.appendChild(rotate_btn);}*/
  
    $('#fakecanvas').append(sticker);
    //drawStickers();
}

// courtesy of https://gist.github.com/derek-dchu/8c828fc40b17646cbb78
function swapElement(a, b) {
  // create a temporary marker div
  var aNext = $('<div>').insertAfter(a);
  a.insertAfter(b);
  b.insertBefore(aNext);
  // remove marker div
  aNext.remove();
}

function brushBtnActive() {
    $('#brush_btn').css({background: "grey" });
    $('#brush_svg').css({stroke: "white"});
    swapElement($('#fakecanvas'),$('#canvas'));
    brushMenuIsOpen = true;
}

function brushBtnDeactive() {
     $('#brush_btn').css({background: "none" });
     $('#brush_svg').css({stroke: "#515151"});
     swapElement($('#fakecanvas'),$('#canvas'));
     brushMenuIsOpen = false;
}

function bgBtnActive() {
    $('#bg_btn').css({background: "grey" });
    $('#bg_svg_circle').css({stroke: "white"});
    $('#bg_svg_path').css({fill: "white"});
    $('#Bg_options').css({visibility: "visible" });
    bgSubmenuIsOpen = true;
}

function bgBtnDeactive() {
     $('#Bg_options').css({visibility: "hidden" });
     $('#bg_btn').css({background: "none" });
     $('#bg_svg_circle').css({stroke: "#515151"});
     $('#bg_svg_path').css({fill: "#515151"});
     bgSubmenuIsOpen = false;
}

function effectBtnActive() {
    $('#effect_btn').css({background: "grey" });
    $('#effect_svg').children().css("fill", "white");
    $('#Effect_options').css({visibility: "visible" });
    effectSubmenuIsOpen = true;
}

function effectBtnDeactive() {
    $('#effect_btn').css({background: "none" });
    $('#effect_svg').children().css("fill", "#515151");
    $('#Effect_options').css({visibility: "hidden" });
    effectSubmenuIsOpen = false;
}

let selected_effect = "none";

$('#fakecanvas').on('click', function(e) {
    if(bgSubmenuIsOpen){
      bgBtnDeactive();
    }
    if(effectSubmenuIsOpen){
      $('#Effect_options').css({visibility: "hidden" });
      effectSubmenuIsOpen = false;
    }
    if(sidebarIsOpen){
      closeSidebar();
    }
    
    if(isDragging == false && isResizing == false && stickModeOn == false){
      if(gifIsFinished || gifIsFinished == undefined){
        if(selected_effect == "bomb"){
          playBombGif(e.pageX, e.pageY);
        } else if (selected_effect == "fire"){
          playFireGif(e.pageX, e.pageY);
        } else if (selected_effect == "water"){
          playWaterGif(e.pageX, e.pageY);
        }
      }
    }
})


function playBombEffect() {
  selected_effect = "bomb";
  $('#effect_option1').css({border: "4px solid black" });
  $('#effect_option2').css({border: "none" });
  $('#effect_option3').css({border: "none" });
}

function playFireEffect() {
  selected_effect = "fire";
  $('#effect_option2').css({border: "4px solid black" });
  $('#effect_option1').css({border: "none" });
  $('#effect_option3').css({border: "none" });
}

function playWaterEffect() {
  selected_effect = "water";
  $('#effect_option3').css({border: "4px solid black" });
  $('#effect_option2').css({border: "none" });
  $('#effect_option1').css({border: "none" });
}

function deselectEffect() {
  selected_effect = "none";
  $('#Effect_options').css({visibility: "hidden" });
  effectSubmenuIsOpen = false;
  effectBtnDeactive();
}

let gifIsFinished;

function playBombGif(x, y) {
  gif = $('<div class="gif" id="bomb_gif"></div>');
  
  $('body').append(gif);
  gifIsFinished = false;

  // position the container to be centered on click
  gif.css('left', x - gif.width() / 2);
  gif.css('top', y - gif.height() / 2);
  
  setTimeout(function(){gif.remove(); gifIsFinished = true;}, 800);
}

function playFireGif(x, y) {
  gif = $('<div class="gif" id="fire_gif"></div>');
  
  $('body').append(gif);
  gifIsFinished = false;

  // position the container to be centered on click
  gif.css('left', x - gif.width() / 2);
  gif.css('top', y - gif.height() / 2);
  
  setTimeout(function(){gif.remove(); gifIsFinished = true;}, 800);
}

function playWaterGif(x, y) {
  gif = $('<div class="gif" id="water_gif"></div>');
  
  $('body').append(gif);
  gifIsFinished = false;

  // position the container to be centered on click
  gif.css('left', x - gif.width() / 2);
  gif.css('top', y - gif.height() / 2);
  
  setTimeout(function(){gif.remove(); gifIsFinished = true;}, 2000);
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
    myDrawImage(c2,background,0,0);
  } else {
    c2.fillStyle = "rgba(0,255,0,255)";
    c2.fillRect(0, 0, canvas2.width, canvas2.height);
  }
  for (const sticker of stickers) {
    //console.log(sticker.firstChild,sticker.firstChild.style.transform,sticker.offsetLeft,sticker.offsetTop);
    var transform1 = sticker.style.transform;
    var transform2 = sticker.firstChild.style.transform;
    var angle = 0;
    var scale = 1;
    if (transform1 && transform1.includes("rotate")) angle = transform1.split("(")[1].split("d")[0];
    if (transform2 && transform2.includes("scale"))  scale = transform2.split("(")[1].split(")")[0];
    var scalex = canvas2.width  / canvas2.offsetWidth;
    var scaley = canvas2.height / canvas2.offsetHeight;
    var x = sticker.offsetLeft * (1280 / canvas2.offsetWidth );
    var y = sticker.offsetTop  * ( 720 / canvas2.offsetHeight);
    myDrawImage(c2,sticker.firstChild,x,y,angle,scale*scalex);
    //console.log("fc:"+fc.offsetWidth+" "+fc.offsetHeight);
    //console.log("sticker:"+sticker.offsetLeft+" "+sticker.offsetTop);
    //console.log("sx sy:"+scalex+" "+scaley);
  }
  c2.drawImage( canvas,0,0 );
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
