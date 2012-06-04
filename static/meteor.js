function Meteor() {
    var _this = this;

    this.ready = false;
    this.callbacks = [];

    this.ws = new WebSocket(document.location.href.replace('http', 'ws') + 'ws_connection');
    this.reactor = new Reactor();

    this.ws.onopen = function() {
        $(function() {
            _this.ready = true;
            _this.onReady();
        })
    }

    this.ws.onmessage = function(event) {
        var data = JSON.parse(event.data);
        callback = _this.reactor.events[data['event']];
        if (callback) callback(data.data);
    }

    this.onReady = function(callback) {
        if (this.ready) {
            if (this.callbacks.length) {
                $.each(this.callbacks, function() {
                    this();
                })
                this.callbacks = []
            }
            if (callback) callback();
        }
        else {
            if (callback) this.callbacks[this.callbacks.length] = callback;
        }
    }

    this.send = function(event) {
        this.ws.send(JSON.stringify(event.message));
    }
}


function Reactor() {
    this.events = {};

    this.addEvent = function(name, callback) {
        this.events[name] = callback;
    }
}

function MeteorEvent(event_name, event_data, callback, options) {
    var opts = $.extend({'autosend': true}, options);
    event_data = event_data || {}

    this.message = {"event": event_name, "data": event_data}
    this.callback = callback;

    if (callback) meteor.reactor.addEvent(event_name, callback);
    if (opts['autosend']) meteor.send(this)
}

var meteor = new Meteor();
