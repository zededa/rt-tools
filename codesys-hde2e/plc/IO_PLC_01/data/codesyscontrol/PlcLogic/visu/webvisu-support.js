//# sourceURL=webvisu-support.js
var CDSWebVisuAccess, IecTypes, TypeIds, PromiseCallbacks, MessageHelper, promiseDict = {}, iPromiseId = 0;

/**
 * Interface between window and iFrame of a Native Element (HTML5 control).
 */
window.addEventListener("message", function (message) {
	if (message.origin !== window["CdsInfo"]["TargetOrigin"])
		return;
	if (message.data === null || message.data === undefined)
		return;
	console.log(message.data);
	MessageHelper.ProcessMessageData(message);
	MessageHelper.ProcessMessageDataWithPromise(message);
});

(function () {
	/** enum {number} with all scalar type classes 
	* @memberof Constants#
	* @readonly
	* @enum {number}
	*/
	IecTypes = {
		/** 0 */
		Bool:		0,
		/** 1 */
		Bit:		1,
		/** 2 */
		Byte:		2,
		/** 3 */
		Word:		3,
		/** 4 */
		DWord:		4,
		/** 5 */
		LWord:		5,
		/** 6 */
		SInt:		6,
		/** 7 */
		Int:		7,
		/** 8 */
		DInt:		8,
		/** 9 */
		LInt:		9,
		/** 10 */
		USInt:		10,
		/** 11 */
		UInt:		11,
		/** 12 */
		UDInt:		12,
		/** 13 */
		ULInt:		13,
		/** 14 */
		Real:		14,
		/** 15 */
		LReal:		15,
		/** 16 */
		String:	16,
		/** 17 */
		WString:	17,
		/** 18 */
		Time:		18,
		/** 19 */
		Date:		19,
		/** 20 */
		DateAndTime:	20,
		/** 21 */
		TimeOfDay:		21
	};
	
	/** enum {number} with all specific type ids 
	* @memberof Constants#
	* @readonly
	* @enum {number}
	*/
	TypeIds = {
		/** 997 */
		Color:		997,
		/** 998 */
		Font:		998
	};
}());


(function()
{
	
	/**
	 * Provides functions that HTML5 elements can call to
	 * interact with IEC code.
	 *
	 * Input to the constructor (Available with Visualization 4.4.0.0): 
	 * width: the width of the element
	 * height: the height of the element
	 *
	 * Before Visualization 4.4.0.0:
	 * Html5 elements cannot access this API directly in the constructor. They need to wait for the iFrame to be loaded. 
	 * Therefore the elements can use the "load" event of the window like this:
	 *	StaticElementElementWrapper = function()
	 *	{
	 *	window.addEventListener("load", this.init);
	 *	}; 
	 */
	CDSWebVisuAccess = function (width, height) {
		var self = this;
		window.addEventListener("load",  function()  { self._postMessage("WebvisuSupportLoaded", {dummyData: "WebvisuSupportLoaded"}, false);});
	};
	
	CDSWebVisuAccess.prototype = {

		/**
		 * Sends a scalar value to IEC code.
		 * @param {String} methodName The method name as configured in the column "Call method" in the HTML5 editor.
		 * @param {*} param The scalar value that will be sent to the IEC application.
		 * @returns {Promise<value>} A promise that is resolved or rejected.
		 */
		sendSimpleValue: function(methodName, param) {
			return this._postMessage("SetValue", {methodName: methodName, param:param}, true);
		},
		
		/**
		 * Checks if a scalar value can be written into the configured variable.
		 * @param {String} methodName The method name as configured in the column "Call method" in the HTML5 editor.
		 * @param {*} param The scalar value that will be sent to the IEC application. Can be number, bigint, date or another type.
		 * @returns {Promise<value>} Promise.Resolve() is called if the value can be written into the specified variable. Otherwise, the promise is rejected.
		 */
		checkSimpleValue: function(methodName, param) {
			return this._postMessage("CheckValue",{methodName: methodName, param:param}, true);
		},
		
		/**
		 * Sends a mouse event for this Html element to the IEC application.
		 * If the element has input actions like 'OnMouseClick' or 'OnMouseDown' configured, these events can be triggered here.
		 * @param {MouseEvent} event The mouse event coming from Javascript code. Event must be of type [MouseEvent]{@link https://developer.mozilla.org/en-US/docs/Web/API/MouseEvent}.
		 * @returns {Promise} A resolved promise. Not relevant.
		 */
		sendMouseEvent: function(event) {
			if (!(event instanceof MouseEvent))
				throw new TypeError("Expected MouseEvent object");
			return this._postMessage("SendMouseEvent",{type: event.type, xPos: event.x, yPos: event.y}, false);
		},
		
		/**
		 * Returns the type description for the corresponding type Id.
		 * Typically the method call of an element has the following signature: function(value, type, typeid) {...}
		 * The value is the value itself and the typeid identifies the type description which provides further information about
		 * the value like size or dimensions in case of an array type.
		 * 
		 * @param {Number} typeId The type Id that comes from the element's method call together with the value.
		 * @returns {Promise<typeDesc>} A promise that contains a JSON object with the members descripted in the type descriptions section starting with TypeDesc..
		 */
		getTypeDesc: function(typeId) {
			return this._postMessage("GetTypeDesc", {typeId: typeId}, true);
		},

		/**
		 * Gets the actual filename of a additional file that can be referenced in the element.
		 * The original filenames are renamed after downloading the application in order to prevent name collisions with other elements.
		 * @deprecated since Visualization 4.3.0.0. Use getTextFile() or getBinaryFile() instead.
		 * @param {String} additionalFile The original name of the file specified in the 'Additional Files' section in the Html5 Editor.
		 * @returns {Promise<resultingAdditionalFileName>} A promise that contains the resulting file name.
		 */
		getAdditionalFile: function(additionalFile) {
			console.info("getAdditionalFile() is deprecated since Visualization 4.3.0.0");
			return this._postMessage("GetAdditionalFileName", {originalAdditionalFileName: additionalFile}, true);
		},

		/**
		 * Gets the actual filename of a provided image file that can be referenced in the element.
		 * The original filenames are renamed after downloading the application in order to prevent name collisions with other elements.
		 * @deprecated since Visualization 4.3.0.0. Use getImageById() instead.
		 * @param {String} imageId The original name of the file specified in the 'Image' section in the Html5 Editor.
		 * @returns {Promise<resultingFileName>} A promise that contains the resulting file name.
		 */
		getImagePoolFileName: function(imageId) {
			console.info("getImagePoolFileName() is deprecated since Visualization 4.3.0.0");
			return this._postMessage("GetImagePoolFileName", {imageId: imageId}, true);
		},

		/**
		 * Creates an HTML image element with the provided image filename as source that can
		 * be used in the html document of the element.
		 * The image source is created by calling the browser function createObjectURL() with the image file's binary content.
		 * It will stay in memory until the HTML5 element gets destroyed.
		 * As this is an asnychronous call a promise containing the Image is returned.
		 * @param {String} filenameFromAdditionalFiles Filename of the image that was declared in the Additional Files section of the HTML5 editor.
		 * @returns {Promise<Image>} A promise that contains a HTML image element.
		 */
		getImageByFilename: function(filenameFromAdditionalFiles) {
			return this._postMessage("GetImageByFilename", {filename: filenameFromAdditionalFiles}, true);
		},

		/**
		 * Creates an HTML image element with the provided image name from an Image Pool as source that can
		 * be used in the html document of the element.
		 * The image source is created by calling the browser function createObjectURL() with the file's binary content.
		 * It will stay in memory until the HTML5 element gets destroyed.
		 * As this is an asnychronous call a promise containing the Image is returned.
		 * @param {String} imagePoolId Path to the image pool and the image id, e.g. "ImagePool.img01".
		 * @returns {Promise<Image>} A promise that contains a HTML image element.
		 */
		getImageById: function(imagePoolId) {
			return this._postMessage("GetImageById", {imagePoolId: imagePoolId}, true);
		},

		/**
		 * Returns the content of a file in text format. The filename must be the same as in the Additional Files section in the HTML5 editor.
		 * As this is an asnychronous call a promise containing the file's content is returned.
		 * @param {String} filenameFromAdditionalFiles Filename of the image that was declared in the Additional Files section of the HTML5 editor.
		 * @returns {Promise<String>} A promise that contains a string with the content of the requested file.
		 */
		getTextFile: function(filenameFromAdditionalFiles) {
			return this._postMessage("GetTextFile", {filename: filenameFromAdditionalFiles}, true);
		},

		/**
		 * Returns the content of a file in binary format. The filename must be the same as in the Additional Files section in the HTML5 editor.
		 * As this is an asnychronous call a promise containing the file's content is returned.
		 * @param {String} filenameFromAdditionalFiles Filename of the image that was declared in the Additional Files section of the HTML5 editor.
		 * @returns {Promise<blob>} A promise that contains a blob object with the content of the requested file.
		 */
		getBinaryFile: function(filenameFromAdditionalFiles) {
			return this._postMessage("GetBinaryFile", {filename: filenameFromAdditionalFiles}, true);
		},
		
		/**
		 * Notifies the IEC application about which parts of the array values should be sent.
		 * Can be used for example with a scrollable table element that only receives the values that are currently visible.
		 * New values may be requested after the user has scrolled.
		 * @param {String} methodName The method name as configured in the column "Call method" in the HTML5 editor.
		 * @param {Number} startIndex Specifies the zero-based start of the array range.
		 * @param {Number} endIndex Specifies the zero-based end of the array range.
		 * @param {Number} scrollDimension The dimension of the array values that should be retrieved.
		 * @returns {Promise} A resolved promise. Not relevant.
		 */
		setScrollRange: function(methodName, startIndex, endIndex, scrollDimension) {
			return this._postMessage("SetScrollRange", {methodName: methodName, startIndex:startIndex, endIndex:endIndex, scrollDimension:scrollDimension}, false);
		},
		
		/**
		 * Checks if a certain value of a complex value (array-like structure) can be written to into the configured variable.
		 * @param {String} methodName The method name as configured in the column "Call method" in the HTML5 editor.
		 * @param {*} param The scalar value that will be sent to the IEC application. Can be of the types number, bigint, date or others.
		 * @param {Number} indexCount Number of dimensions of the configured datatype. E.g. 2 for a simple table. Maximum is 3.
		 * @param {Number} index0 Zero-Based index in the first dimension.
		 * @param {Number} index1 Zero-Based index in the second dimension.
		 * @param {Number} index2 Zero-Based index in the third dimension.
		 * @returns {Promise<value>} Resolve() is called if the value can be written into the specified variable. Otherwise, the promise is rejected.
		 */
		checkComplexValue: function(methodName, param, indexCount, index0, index1, index2) {  // 
			return this._postMessage("CheckComplexValue", {methodName: methodName, param:param, indexCount:indexCount, index0:index0, index1:index1, index2:index2}, true);
		},
		
		/**
		 * Sends a certain value of a complex value (array-like structure) to the configured variable in the application.
		 * @param {String} methodName The method name as configured in the column "Call method" in the HTML5 editor.
		 * @param {*} param The scalar value that will be sent to the IEC application.
		 * @param {Number} indexCount Number of dimensions of the configured datatype. E.g. 2 for a simple table. Maximum is 3.
		 * @param {Number} index0 Zero-Based index in the first dimension.
		 * @param {Number} index1 Zero-Based index in the second dimension.
		 * @param {Number} index2 Zero-Based index in the third dimension.
		 * @returns {Promise<value, indexCount, index0, index1, index2>} A promise that is resolved or rejected.
		 */
		sendComplexValue: function(methodName, param, indexCount, index0, index1, index2) {
			return this._postMessage("SetComplexValue",{methodName: methodName, param:param, indexCount:indexCount, index0:index0, index1:index1, index2:index2}, true);
		},

		/**
		 * Internal Helper function to send messages from the element's iFrame to the webvisu.
		 */
		 _postMessage: function(messageType, data, awaitsResponse) {
			if (window["CdsInfo"]["TargetOrigin"] === undefined) {
				throw new TypeError("TargetOrigin is not yet set.");
			}
			var promiseId, promise;
			if (awaitsResponse) {
				promiseId = iPromiseId;
				promise = new Promise(function (resolve, reject) {
				promiseDict[iPromiseId] = new PromiseCallbacks(resolve, reject);
				});
				iPromiseId++;
			} else {
				promiseId = null;
				promise = Promise.resolve();
			}
			window.parent.postMessage({type:messageType, data: data, promiseId: promiseId, identification: window["CdsInfo"]["Identification"]}, window["CdsInfo"]["TargetOrigin"]);
			return promise;
		}
	};
}());

(function()
{
	/**
	 * Internal class to capsulate promises.
	 */
	PromiseCallbacks = function (resolve, reject){
		this.resolve = resolve;
		this.reject = reject;
	};

	PromiseCallbacks.prototype = {

		getResolveCallback: function() {
			return this.resolve;
		},

		getRejectCallback: function() {
			return this.reject;
		}
	};
}());

(function () {
	/**
	 * Internal helper class to process messages.
	 */
	MessageHelper = function () {
		// empty constructor
	};

	MessageHelper.GetPromiseCallback = function (message) {
		var promiseId = message.data.data.promiseId, promiseCallbacksHelp = null;
		if (promiseId !== undefined) {
			promiseCallbacksHelp = promiseDict[promiseId];
			if (promiseCallbacksHelp === undefined) {
				promiseCallbacksHelp = null;
			} else {
				delete promiseDict[promiseId];
			}
		}
		return promiseCallbacksHelp;
	};

	MessageHelper.ProcessMessageData = function (message) {
		var messageData = message.data;
		if (messageData.type === "MethodCall") {
			var methodName = messageData.data.methodName;
			var methodNameComponents = methodName.split(".")
				, method = window["CdsInfo"]["Wrapper"];
			for (var i = 0; i < methodNameComponents.length - 1; ++i)
				method = method[methodNameComponents[i]]();
			method[methodNameComponents[methodNameComponents.length - 1]].apply(method, messageData.data.params);
		}
		else if (messageData.type === "Resize") {
			var docBody = document.body;
			docBody.style.width = messageData.data.width + 'px';
			docBody.style.height = messageData.data.height + 'px';
			docBody.style.overflow = "hidden";
		}
	};

	MessageHelper.ProcessMessageDataWithPromise = function (message) {
		var promiseCallbacksHelp = MessageHelper.GetPromiseCallback(message), isAccepted = message.data.data.result, messageData = message.data;
		if (promiseCallbacksHelp == null)
			return;
		switch (messageData.type) {
			case "ErrorMessage":
				promiseCallbacksHelp.getRejectCallback()(messageData.data.error);
				break;
			case "CheckSimpleValueResult":
			case "SetSimpleValueResult":
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, messageData.data.value);
				break;
			case "GetTypeDescResult":
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, messageData.data.typeDesc);
				break;
			case "GetAdditionalFileNameResult":
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, messageData.data.resultingAdditionalFileName);
				break;
			case "GetImageMessageResult":
			case "GetImageByIdMessageResult":
				var imageElem = new Image();
				imageElem.src = window.URL.createObjectURL(messageData.data.responseContent);
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, imageElem);
				break;
			case "GetTextFileMessageResult":
			case "GetBinaryFileMessageResult":
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, messageData.data.responseContent);
				break;
			case "GetImagePoolFileNameResult":
				MessageHelper.SendDataToPromiseCallback(promiseCallbacksHelp, isAccepted, messageData.data.resultingFileName);
				break;
			case "CheckComplexValueResult":
			case "SetComplexValueResult":
				if (isAccepted)
					promiseCallbacksHelp.getResolveCallback()(messageData.data.value, messageData.data.indexCount, messageData.data.index0, messageData.data.index1, messageData.data.index2);
				else
					promiseCallbacksHelp.getRejectCallback()(messageData.data.value, messageData.data.indexCount, messageData.data.index0, messageData.data.index1, messageData.data.index2);
				break;
		}
	};

	MessageHelper.SendDataToPromiseCallback = function (promiseCallbacksHelp, isAccepted, params) {
		if (isAccepted)
			promiseCallbacksHelp.getResolveCallback()(params);
		else
			promiseCallbacksHelp.getRejectCallback()(params);
	};
}());

window["CDSWebVisuAccess"] = new CDSWebVisuAccess();
window["IecTypes"] = IecTypes;
window["TypeIds"] = TypeIds;