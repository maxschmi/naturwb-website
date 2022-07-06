let enum_references = function(){
  // the references need to be in the format <sup><a href="#quelle-bla"></a></sup>
  let references = $("sup>a[href*='#quelle-']");
  let sources = $("div.quellen li");
  let find_source = function(ref){
    let id = ref.href.split("#")[1];
    let num = NaN;
    for (let source of sources){
      if (source.id==id){return source}
    }
  }
  for (ref of references){
    let source = find_source(ref);
    ref.textContent = sources.index(source)+1;
  }
}
enum_references();