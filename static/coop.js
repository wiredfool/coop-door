
/*
 * Door controller javascript.
 *
 */

/* globals $
*/



var sock = new WebSocket('ws://'+ document.location.host + '/status');
var elt = $('#status');
var current_status = {}

if (sock) {
    sock.onopen = function () {
        elt.html('Connected! Awaiting status...');
		sock.send('ping');
    };
    sock.onmessage = function (event) {
		var status = parse_response(event.data)
        elt.html(JSON.stringify(status))
		update_svg(status)
		current_status = status;
    };
    sock.onclose = function () {
        elt.html('no data');
    };

}

$('form.inline').submit(function(e){
    $.post(this.action);
	return false;
})


function parse_response(s) {
	var elts = s.split('\n')
	console.log(elts)
	var status ={}
	if (elts.length){
		try {
			status = JSON.parse(elts[elts.length-1])
		} catch(e) {
			console.log(e)
		}
	}
	return status
}

function update_svg(status) {
	$('#door').removeClass()
	$('#door').addClass(status.state)
	if (status.upper){
		$('#door').addClass('upper')
	}
	if (status.lower){
		$('#door').addClass('lower')
	}

}