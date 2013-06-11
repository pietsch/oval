$(function() {
  var button = $('#submit-link');
  var form = $('#valform');
  var results = $('div#results');
  var loader = $('span#loader');
  loader.hide();

  button.click( function() {
    form.submit();
    return false;
  }).show();


  if (form.length < 0)
    return;

  form.submit(function() {
    var url = $('input[name="basic_url"]', this).val();
     if ( $.trim(url) == '') {
      return;
    }
    results.fadeOut("slow");
    form.hide();
    loader.show();
  
      $.ajax({type: "POST", url: '/_validate', data:{basic_url: url}, success: function(data) {
      loader.hide();
      form.show();
      results.html(data);
      results.fadeIn("fast");
    }});
    return false;
  });
});