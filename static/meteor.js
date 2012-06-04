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
        var map = _this.reactor.events[data['event']];
        var callback = data.timestamp ? map[data.timestamp] : map.default;
        if (callback) callback(data.data);

        if (data.timestamp) {
            delete _this.reactor.events[data['event']][data.timestamp];
        }
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

    this.addEvent = function(args) {
        var options = $.extend({
            name: '', callback: null, timestamp: null
        }, args);

        if ((options.name) && (options.callback)) {
            var key = options.timestamp ? options.timestamp : 'default';
            if (!this.events[options.name]) {
                this.events[options.name] = {}
            }
            this.events[options.name][key] = options.callback;
        }
    }
}

function MeteorEvent(args) {
    var options = $.extend({
        name: '',
        data: {},
        callback: null,
        autosend: true
    }, args);

    this.message = {"event": options.name, "data": options.data}
    this.callback = options.callback;

    var timestamp = options.callback ? (new Date).getTime() : null
    if (timestamp) this.message.timestamp = timestamp;

    if (options.callback) {
        meteor.reactor.addEvent({
            name: options.name,
            callback: options.callback,
            timestamp: timestamp
        });
    }
    if (options.autosend) meteor.send(this);
}

var meteor = new Meteor();
