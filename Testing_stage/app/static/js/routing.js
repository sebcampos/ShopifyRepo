// Note: This example requires that you consent to location sharing when
// prompted by your browser. If you see the error "The Geolocation service
// failed.", it means you probably did not give permission for the browser to
// locate you.
console.log("working");
let map; 
let infoWindow;

function initMap() {
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 37.4356173, lng: -122.4281 },
    zoom: 6,
  });
  var directionsService = new google.maps.DirectionsService();
  var directionsRenderer = new google.maps.DirectionsRenderer();
  directionsRenderer.setMap(map);
  infoWindow = new google.maps.InfoWindow();
  const locationButton = document.createElement("button");
  locationButton.textContent = "Route";
  locationButton.classList.add("custom-map-control-button");
  map.controls[google.maps.ControlPosition.TOP_CENTER].push(locationButton);
  locationButton.addEventListener("click", () => {
    // Try HTML5 geolocation.
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const pos = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };
          const pos2 = {
            lat: Number(v_lat),
            lng: Number(v_lng)
          }
          let new_waypts = [];
          for (let i = 0; i < waypts.length; i++) {
            let first = waypts[i].lat;
            let second = waypts[i].lng;
            let pos = new google.maps.LatLng(first,second)
            new_waypts.push({
                location: pos,
                stopover: true
            })
          }
          infoWindow.setPosition(pos);
          infoWindow.setContent("Current location.");
          infoWindow.open(map);
          map.setCenter(pos);
          var request = {
            origin: new google.maps.LatLng(pos),
            destination: new google.maps.LatLng(pos2),
            waypoints: new_waypts,
            optimizeWaypoints: true,
            travelMode: 'DRIVING'
          }
          directionsService.route(request, function(response,status) {
            if (status == 'OK' ) {
              console.log(response);
              directionsRenderer.setDirections(response);
            }
          });
        },

        () => {
          handleLocationError(true, infoWindow, map.getCenter());
        }
      );

    } else {
      // Browser doesn't support Geolocation
      handleLocationError(false, infoWindow, map.getCenter());
    }
  });
};

function handleLocationError(browserHasGeolocation, infoWindow, pos) {
  infoWindow.setPosition(pos);
  infoWindow.setContent(
    browserHasGeolocation
      ? "Error: The Geolocation service failed."
      : "Error: Your browser doesn't support geolocation."
  );
  infoWindow.open(map);
}