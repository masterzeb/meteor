$(function() {
    $("#username").focus();
    $("#auth_form").submit(function(e) {
        if (!$("#username").val()) {
            e.preventDefault();
        }
    })
})