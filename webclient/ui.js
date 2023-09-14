let bgSubmenuIsOpen = false;
let effectSubmenuIsOpen = false;
let brushMenuIsOpen = false;
let sidebarIsOpen = false;
let stickModeOn = false;

// courtesy of https://gist.github.com/derek-dchu/8c828fc40b17646cbb78
function swapElement(a, b) {
  // create a temporary marker div
  var aNext = $('<div>').insertAfter(a);
  a.insertAfter(b);
  b.insertBefore(aNext);
  // remove marker div
  aNext.remove();
}

$('#effect_btn').on("click", function() {
  effectBtnActive();  
  bgBtnDeactive();
  brushBtnDeactive();
  stickModeOn = false;
});

$('#stickers_btn').on("click", function() {
if(sidebarIsOpen==false)  {
  openSidebar();
} else {
  closeSidebar();
}
});

function openSidebar() {
  $('#side_panel').css({ width: "450px" });
  $('#side_panel').css({ padding: "0px 0px 0px 42px" });
  $('#stickers_btn').css({ right: "442px" });
  $('#stickers_btn').css({ transform: "rotate(180deg)" });
  $('#stickers_btn').css({ background: "white" });
  sidebarIsOpen = true;
  stickModeOn = true;
  bgBtnDeactive();
  effectBtnDeactive();
}

function closeSidebar() {
  $('#side_panel').css({ width: "0px" });
  $('#side_panel').css({ padding: "0px" });
  $('#stickers_btn').css({ right: "0px" });
  $('#stickers_btn').css({ transform: "rotate(360deg)" });
  $('#stickers_btn').css({ background: "rgba(230, 230, 230, 0.7)" });
  sidebarIsOpen = false;
}

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
