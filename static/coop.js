
/*
 * Door controller javascript.
 *
 */

/* globals $
*/



var sock = new WebSocket('ws://'+ document.location.host + '/status');
var elt = $('#status');

if (sock) {
    sock.onopen = function () {
        elt.html('Connected! Awaiting status...');
		sock.send('ping');
    };
    sock.onmessage = function (event) {
        elt.html(event.data);
    };
    sock.onclose = function () {
        elt.html('no data');
    };

}

$('form.inline').submit(function(e){
    $.post(this.action);
	return false;
})
