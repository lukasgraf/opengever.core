(function(global, $) {

  var settings = {
    overwrite: false, // Do not reload the tooltip when it's already created
    content: { text: tooltipContent }, // Set ajax content
    position: {
      target: "mouse", // Set tooltip position relative to the current mouse location
      viewport: $(window), // The tooltip must not leave the window
      adjust: {
        mouse: false, // Do not track the mouse
        method: "shift", // Set the x,y coordinates when the tooltip should leave the viewport
        x: 20, // Slighly shift the location in x direction
        y: 20 // Slighly shift the location in y direction
      },
      effect: false // Do not animate the tooltip loaction changes
    },
    show: {
      solo: true, // Make sure that only one tooltip is visible
      effect: false, // Show the tooltip immediately
      ready: true, // Make sure that the tooltip gets shown immediately when it's ready
      delay: 300 // The tooltip gets shown after 300ms
    },
    hide: {
      delay: 300, // The tooltip gets hidden after 300ms
      effect: false, // Hide the tooltip immediately
      fixed: true // Make sure the tooltip gets not hidden if mouse is over the tooltip
    },
    events: {
      show: closeTooltips
    }
  };

  function spinner() { return '<img src="' + $("head > base").attr("href") + '/spinner.gif" class="spinner"/>'; }

  function failure(status, error) { return status + ": " + error; }

  function tooltipContent(event, api) {
    $.get($(event.currentTarget).data("tooltip-url"))
      .done(function(data) {
        api.set("content.text", data);
        $(document).trigger('tooltip.show', [api]);
        $(".showroom-reference").on("click", function() { api.hide(); });
      })
      .fail(function(xhr, status, error) { api.set("content.text", failure(status, error)); });
    return spinner();
  }

  function initTooltips(event) { $(event.currentTarget).qtip(settings, event); }

  function closeTooltips(event, api) { $(event.originalEvent.target).on("click", function() { api.hide(); }); }

  $(document).on("mouseover", ".tooltip-trigger", initTooltips);

}(window, jQuery));
