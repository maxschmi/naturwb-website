// funtion to geoencode
let geoencode = async function(name){
  let request = new Request(
    `https://nominatim.openstreetmap.org/search?q=${name},germany&polygon_geojson=1&format=geojson`,
    {methode: "GET"});

    let return_feature = await fetch(request).then(response => response.json().then(json => {
      for (let feature of json["features"]){
        if (["Polygon", "MultiPolygon"].includes(feature["geometry"]["type"])){
          return feature;
        }
      }
    }));
    console.log(return_feature.geometry);
    return return_feature.geometry;    
}

// add Events listener to search box
let searchForm = document.getElementById("geoencodeSearchForm");
if (searchForm !== null){
  searchForm.addEventListener("submit", async (e) =>  {
    e.preventDefault();
    let name = e.target.querySelector("input#id_search_query").value;
    let geometry = await geoencode(name);
    add_geometry_to_map(geometry);
  });
}