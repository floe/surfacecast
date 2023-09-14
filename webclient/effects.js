let selected_effect = "none";

$('#fakecanvas').on('click', function (e) {
  if (bgSubmenuIsOpen) {
    bgBtnDeactive();
  }
  if (effectSubmenuIsOpen) {
    $('#Effect_options').css({ visibility: "hidden" });
    effectSubmenuIsOpen = false;
  }
  if (sidebarIsOpen) {
    closeSidebar();
  }

  if (isDragging == false && isResizing == false && stickModeOn == false) {
    if (gifIsFinished || gifIsFinished == undefined) {
      if (selected_effect == "bomb") {
        playBombGif(e.pageX, e.pageY);
      } else if (selected_effect == "fire") {
        playFireGif(e.pageX, e.pageY);
      } else if (selected_effect == "water") {
        playWaterGif(e.pageX, e.pageY);
      }
    }
  }
});

function playBombEffect() {
  selected_effect = "bomb";
  $('#effect_option1').css({ border: "4px solid black" });
  $('#effect_option2').css({ border: "none" });
  $('#effect_option3').css({ border: "none" });
}

function playFireEffect() {
  selected_effect = "fire";
  $('#effect_option2').css({ border: "4px solid black" });
  $('#effect_option1').css({ border: "none" });
  $('#effect_option3').css({ border: "none" });
}

function playWaterEffect() {
  selected_effect = "water";
  $('#effect_option3').css({ border: "4px solid black" });
  $('#effect_option2').css({ border: "none" });
  $('#effect_option1').css({ border: "none" });
}

function deselectEffect() {
  selected_effect = "none";
  $('#Effect_options').css({ visibility: "hidden" });
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

  setTimeout(function () { gif.remove(); gifIsFinished = true; }, 800);
}

function playFireGif(x, y) {
  gif = $('<div class="gif" id="fire_gif"></div>');

  $('body').append(gif);
  gifIsFinished = false;

  // position the container to be centered on click
  gif.css('left', x - gif.width() / 2);
  gif.css('top', y - gif.height() / 2);

  setTimeout(function () { gif.remove(); gifIsFinished = true; }, 800);
}

function playWaterGif(x, y) {
  gif = $('<div class="gif" id="water_gif"></div>');

  $('body').append(gif);
  gifIsFinished = false;

  // position the container to be centered on click
  gif.css('left', x - gif.width() / 2);
  gif.css('top', y - gif.height() / 2);

  setTimeout(function () { gif.remove(); gifIsFinished = true; }, 2000);
}
