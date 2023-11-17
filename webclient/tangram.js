// disable the canvas painting
function onCanvasDown(evt) { }
function onCanvasUp(evt) { }
function onCanvasMove(evt) { }

// directly add one sticker (= puzzle piece) each
window.addEventListener("load", function(ev) {
add_sticker(document.getElementById("t1"));
add_sticker(document.getElementById("t2"));
add_sticker(document.getElementById("t3"));
add_sticker(document.getElementById("t4"));
add_sticker(document.getElementById("t5"));
add_sticker(document.getElementById("t6"));
add_sticker(document.getElementById("t7"));
});
