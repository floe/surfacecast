var mousedown;
var mycolor;
var x,y;
var scale = 1;

function paint(ctx, centerX, centerY, clearcolor, clearmode, erase) {
    const radius = (erase == 1) ? 5 : 20;
    ctx.beginPath();
    ctx.lineWidth = radius;
    ctx.strokeStyle = (erase == 1) ? mycolor : clearcolor;
    ctx.fillStyle = ctx.strokeStyle
    ctx.globalCompositeOperation = (erase == 1) ? "source-over" : clearmode;
    ctx.moveTo(x,y);
    ctx.lineTo(centerX,centerY);
    ctx.stroke();
    ctx.arc(centerX, centerY, radius/2, 0, 2 * Math.PI, false);
    ctx.fill();
    ctx.closePath();
  }
  
  
function onCanvasDown(evt) { x = evt.offsetX/scale; y = evt.offsetY/scale; mousedown = (evt.buttons == undefined) ? 1 : evt.buttons; }
function onCanvasUp  (evt) { onCanvasMove(evt);                            mousedown = 0;                                            }
  
function onCanvasMove(evt) {

  if (mousedown == 0) return;

  if (evt.type == "touchmove") {
    evt.preventDefault();
    evt.offsetX = evt.changedTouches[0].pageX;
    evt.offsetY = evt.changedTouches[0].pageY;
  }

  const centerX = evt.offsetX / scale;
  const centerY = evt.offsetY / scale;

  paint(canvasctx, centerX, centerY, "rgba(0,  0,0,255)", "destination-out", mousedown);
  paint(sourcectx, centerX, centerY, "rgba(0,255,0,255)", "source-over",     mousedown);

  x = centerX;
  y = centerY;
}

function canvas_init() {
  canvas.onmousedown  = onCanvasDown;
  canvas.ontouchstart = onCanvasDown;
  canvas.onmouseup    = onCanvasUp;
  canvas.ontouchend   = onCanvasUp;
  canvas.onmousemove  = onCanvasMove;
  canvas.ontouchmove  = onCanvasMove;

  canvas.addEventListener("contextmenu", function(e) { e.preventDefault(); } );
  scale = canvas.offsetWidth / canvas.width;

  var colors = ["red", "cyan", "yellow", "blue", "magenta" ];
  mycolor = colors[Math.floor(Math.random() * colors.length)];
}