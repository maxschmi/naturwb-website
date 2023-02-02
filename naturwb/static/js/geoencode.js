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
    return "Error";
  }));
  if (return_feature != "Error"){
    return return_feature.geometry;
  }else{
    return "Error";
  } 
}

// add Events listener to search box
let searchForm = document.getElementById("geoencodeSearchForm");
if (searchForm !== null){
  searchForm.addEventListener("submit", async (e) =>  {
    e.preventDefault();
    let name = e.target.querySelector("input#id_search_query").value;
    let btn = e.target.querySelector("input#btn_search_query");
    let error_msg = e.target.querySelector("div#error_search_query");
    
    let geometry = await geoencode(name);

    if (geometry != "Error"){
      btn.classList.remove("btn-danger");
      btn.classList.add("btn-primary");
      error_msg.hidden=true;
      add_geometry_to_map(geometry);
    } else {
      btn.classList.remove("btn-primary");
      btn.classList.add("btn-danger");
      error_msg.hidden=false;
    }
  });
}