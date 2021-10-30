// Button click: datei auswählen
let btnLoad = document.getElementById("btnLoad")
if (btnLoad !== null){
  btnLoad.addEventListener("click", e => {
    // prompt for file
    let inputFile = document.getElementById("FileInput");
    inputFile.click();

  });
}

// nachdem Datei ausgesucht: datei in map laden
let inputFile = document.getElementById("FileInput");
if (inputFile !== null){
  inputFile.addEventListener("input", e =>{
    // stop if no file selected
    if (e.target.files.length == 0){
      return;
    }

    // read file
    let file = e.target.files[0];
    file.arrayBuffer().then((bufferResult) => {
      if (file.name.match(/^.*\.zip$/)){
        shp.parseZip(bufferResult).then((geojson) => {
          if (geojson.features.length == 0){
            alert("Es konnte kein Polygon in ihrer Datei gefunden werden!");
          } else {
            if (geojson.features.length > 1) {
              alert("In ihrer Datei wurde mehr als ein Polygon gefunden, allerdings wird nur das erste geladen!\n Wenn Sie ein Gebiet aus mehreren Polygonen untersuchen wollen, vereinigen Sie diese im Vorfeld zu einem MultiPolygon.");
            }
            add_geometry_to_map(geojson.features[0].geometry);
          }
        });
      // } else if (file.name.match(/^.*\.shp$/)) {
      //   shp.parseShp(bufferResult).then((geojson) => {
      //     add_geometry_to_map(geojson.features[0].geometry);
      //   });
      } else {
        alert("Ihre Datei konnte leider nicht reingeladen werden!\nÜberprüfen Sie diese. Es muss ein ZIP-Ordner, mit den Shape-Dateien eines Polygons sein.");
      }
    });
    // reset input field
    e.target.value = "";
  });
}

let add_geometry_to_map = function(geometry){
  console.log(geometry);
  // write in form
  document.getElementById("id_geom").value = JSON.stringify(geometry);

  // delete previous polygons on map
  let map = maps[0];
  map.eachLayer(layer => {
    if (layer._path !== undefined){
        maps[0].removeLayer(layer);
    }
  });
  
  // load to map
  let geometryField = new L.GeometryField(geodjango_id_geom);
  geometryField.addTo(map);

  // delete previous drawing utilities
  let drawUtilities = document.querySelectorAll(".leaflet-control-container > div > .leaflet-draw.leaflet-control.id_geom");
  if (drawUtilities.length > 1){
    drawUtilities[0].remove();
  }

  // delete circle draw Marker
  let cms = document.querySelectorAll(".leaflet-draw-draw-circlemarker");
  cms.forEach(el => el.remove());
}