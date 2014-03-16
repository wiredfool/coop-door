/*
 * Door controller javascript. 
 * 
 */

/* globals $
*/



var sock = window.WebSocket('ws:/status');
var elt = $('#status');

if (sock) {
    sock.onopen = function () {
        elt.html('Connected! Awaiting status...');
    };
    sock.onmessage = function (event) {
        elt.html(event.data);
    };
    sock.onclose = function () {
        elt.html('no data');
    };
    sock.send('ping');
} 

$('form.inline').submit(function(e){
    $.post(this.action);
})
