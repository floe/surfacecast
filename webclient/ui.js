let bgSubmenuIsOpen = false;
let effectSubmenuIsOpen = false;
let brushMenuIsOpen = false;

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
  swapElement($('#fakecanvas'),$('#surfacecanvas'));
  brushMenuIsOpen = true;
}

function brushBtnDeactive() {
   $('#brush_btn').css({background: "none" });
   $('#brush_svg').css({stroke: "#515151"});
   swapElement($('#fakecanvas'),$('#surfacecanvas'));
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
