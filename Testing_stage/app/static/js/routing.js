// Note: This example requires that you consent to location sharing when
// prompted by your browser. If you see the error "The Geolocation service
// failed.", it means you probably did not give permission for the browser to
// locate you.

let map; 
let infoWindow;

function initMap() {
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: -34.397, lng: 150.644 },
    zoom: 6,
  });
  let lat = document.getElementById("lat").textContent;
  let lng = document.getElementById("lng").textContent;
  let foo = document.getElementById("waypoints").textContent
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
            lat: Number(lat),
            lng: Number(lng)
          }
          infoWindow.setPosition(pos);
          infoWindow.setContent("Current location.");
          infoWindow.open(map);
          map.setCenter(pos);
          let waypts = [];
          let newArray = foo.split(",")
          console.log(newArray);
          for (let i = 0; i < newArray.length / 2; i++ ) {
              console.log(newArray[i],newArray[i+1]);
              let new_lat = Number(newArray[i]);
              let new_lng = Number(newArray[i+1]);
              let i = i + 2
              const pos_way = new google.maps.LatLng({
                lat: new_lat,
                lng: new_lng});
              waypts.push({
                location: pos_way,
                stopover: true
              });
            };
          console.log(waypts);
          var request = {
            origin: new google.maps.LatLng(pos),
            destination: new google.maps.LatLng(pos2),
            waypoints: waypts,
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