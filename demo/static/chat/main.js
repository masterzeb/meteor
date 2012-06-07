meteor.onReady(function() {
    // define resize function
    function resizeFunc() {
        $("#chat").height($('body').height() - 115);
    }

    // define append message function
    function appendMessage(msg, user) {
        $("#chat").append(
            '<br />' + (user ? '<b><i>[' + user + ']</i></b>: ' : '') + '<span' + (user ? '>' : ' class="system">*') + msg + '</span>'
        );
    }

    // apply resize
    $(window).resize(resizeFunc);
    resizeFunc();

    // add key down event
    $("#message").keydown(function (e) {
        if (e.ctrlKey && e.keyCode == 13) {
            var msg = $(this).val();
            if (msg) {
            $(this).val('');
                new MeteorEvent({
                    name: 'chat/new_message',
                    data: {'msg': msg}
                })
            }
        }
    })

    // add enter user event handling
    meteor.reactor.addEvent({
        name: 'user_enter',
        callback: function(data) {
            appendMessage('User "' + data.user + '" joined the chat');
        }
    });

    // add leave user event handling
    meteor.reactor.addEvent({
        name: 'user_leave',
        callback: function(data) {
            appendMessage('User "' + data.user + '" leave the chat');
        }
    });

    // add recive message event
    meteor.reactor.addEvent({
        name: 'chat/new_message',
        callback: function(data) {
            appendMessage(data.msg, data.user);
        }
    });
});