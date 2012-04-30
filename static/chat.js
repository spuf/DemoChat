WEB_SOCKET_SWF_LOCATION = "/static/WebSocketMain.swf";
WEB_SOCKET_DEBUG = false;

$(document).ready(function() {
	if (!window.console) window.console = {};
	if (!window.console.log) window.console.log = function() {};

	$('#post').attr('disabled', 'disabled');
	
	$("#messageform").live("submit", function() {
		newMessage($(this));
		return false;
	});
	$("#messageform").live("keypress", function(e) {
		if (e.keyCode == 13) {
			newMessage($(this));
			return false;
		}
	});
	$("#message").select();
	updater.start();
	setInterval(checkCount, 10000);
	checkCount();
});

function newMessage(form) {
	var message = form.formToDict();
	updater.socket.send(JSON.stringify(message));
	form.find("input[type=text]").val("").select();
}

jQuery.fn.formToDict = function() {
	var fields = this.serializeArray();
	var json = {}
	for (var i = 0; i < fields.length; i++) {
		json[fields[i].name] = fields[i].value;
	}
	if (json.next) delete json.next;
	return json;
};

var updater = {
	socket: null,

	start: function() {
		updater.socket = new WebSocket('ws://'+document.location.host+'/chatsocket');
		
		updater.socket.onmessage = function(event) {
			updater.showMessage(JSON.parse(event.data));
		}
		
		updater.socket.onopen = function(event) {
			$('#post').removeAttr('disabled');
		}
		
		updater.socket.onclose = function () {
			if (confirm('Socket disconnected.\nReload this page?'))
				document.location.reload();
		}
	},

	showMessage: function(message) {
		var existing = $("#m" + message.id);
		if (existing.length > 0) return;
		var node = $(message.html);
		node.hide();
		$("#inbox").append(node);
		node.slideDown();
	}
};

function checkCount() {
	$('#count').load('/count');
}