# Introduction
This SDK client provides a comprehensive toolset for interacting with the ICICI Banking services.
The SDK simplifies integration with the APIs and provides customizable configuration options for users.
This manual will guide through building, configuring, and integrating with deployable components.

# Merchant Integration
The Merchant receives the SDK Client Distribution in a zip file named Python_Eazypay_v1.zip.zip 

Unzip the file and follow Readme.md file from src folder.

# Verify the sdk-distribution zip File
Check the deliverables received and ensure it is shared securely through a proper channel.
Use sdk-distribution-hashes.txt with SHA-256 to verify the integrity and ensure contents are not corrupted.

To verify the zip file open any terminal/command prompt tool in your machine.
To verify the SHA-256 Hash follow below commands.

Run the following command, replacing path\to\Python_Eazypay_v1.zip.zip with the actual path to Python_Eazypay_v1.zip.zip zip file:

For Windows machine use the following Get-FileHash tool Comand to use:
Get-FileHash -Algorithm SHA256 "path\to\Python_Eazypay_v1.zip.zip"

When using a Command Prompt without PowerShell, need to use tools like certutil:
certutil -hashfile "path\to\Python_Eazypay_v1.zip.zip" SHA256

On Linux/macOS machine

Run the following command, replacing path/to/Python_Eazypay_v1.zip.zip with the actual path to Python_Eazypay_v1.zip.zip

zip file: shasum -a 256 path/to/Python_Eazypay_v1.zip.zip 

Alternative Command (if shasum is not available): sha256sum path/to/Python_Eazypay_v1.zip.zip

Compare the output hash with the SHA-256 hash stored in sdk-client-hash.txt with  hash present in sdk-distribution-hashes.txt (Provided).

If the hashes match, the file’s integrity is verified successfully, start with Unzip process. otherwise contact support team.

# Unzip the Python_Eazypay_v1.zip.zip 
Unzip the contents safely using tar (Unix) or unzip (Windows) commands.
Unzip commands to verify in Windows or Unix environments.

.tar command for Windows (Command Prompt or PowerShell)

tar -xf Python_Eazypay_v1.zip.zip  

.unzip command for Unix (Linux or macOS Terminal)

unzip Python_Eazypay_v1.zip.zip  

# folder structure looks like below:

sdk-distribution/
├── src/
│   ├── eazypay/
│   │   ├── modal/
│   │   │   ├── requrest
│   │   │   ├── response
│   │   │   ├── __init__.py
│   │   └── __init__.py
│   │   └── api.py
│   ├── eazypay-egg-info/
│   │   ├── PKG-INFO
│   │   ├── SOURCES.txt
│   │   ├── top_level.txt
│   │   └── dependency_links.txt
│   ├── httpcore/
│   │   ├── config/
│   │   ├── dto/
│   │   ├── http/
│   │   ├── utils/
│   │   └── package.json
├── MANIFEST.in
├── PKG-INFO
├── pyproject
├── README
├── sdk-builder-config
├── setup

## System Requirements
Now before integrating ensure the following System requirements are met.

To ensure compatibility, make sure the system meets the following requirements:
- *Python Version*: 3.9.16 or above

## Using the SDK Client 
Here's a detailed explanation for using the SDKClient.execute method as an entry point for interacting with APIs. <br>

The SDKClient.execute method provides a unified interface for making API calls across different modules and endpoints. <br>
By accepting a generic response type, this method supports multiple APIs and simplifies API integration. <br>
Developers only need to know the apiId, module,function  and corresponding DTOs to call any API within the SDK.

This includes the syntax, usage, and an overview of how to use this method to call different APIs by specifying modules and DTOs. <br>
To use the SDK Client, make calls by invoking a single method:
python
response = function(dto( **payload))



## Integrating the APIs
Go to the folder Python_SDK/sdk_builder_config.json <br>
All the collection of API configurations are available here categorized by products.<br>
Choose the products you want to integrate with. For example, if selecting Composite, only the Composite folder and the http-core folder are required. <br>
For Composite server-public-key.pem,corporate_Server_Publickey.pem are required.

For example, if cibBulk is required then cibBulk Folder,http-core folder with corporate_Server_Publickey.pem

Module wise collection looks like this:
json
{
	"eazypay": {
		"headers": {},
		"apis": [
			{}
		]
	}
}

The API Configuration for a API looks like this:
json
{  
  "apiId": "3015",
  "apiName": "QR3",
  "basePath": "/MerchantAPI/UPI/v0",
  "endpoint": "/QR3",
  "method": "POST",
  "requestDtoType": "QR3RequestDTO",
  "responseDtoType": "QR123ResponseDTO" ,
  "function" : "qr3"
  }


### API JSON Configuration Explained

This JSON configuration provides details for a specific API, named *"UPIPaymentRequestDto,"* which is used for making API calls for Bulk Pyment. Each field in this JSON defines critical information necessary to integrate with and make requests to the API.

JSON Fields Explained
apiId: "3001"

A unique identifier for the API. This ID is often used by the SDK or client application to identify the API configuration for "Bulk Paymen."
apiName: "TransactionStatus"

A descriptive name for the API, indicating the functionality it provides. In this case, it retrieves Upipaymentstatus-related information.
description: "TransactionStatus"

Additional information or description of the API, explaining its purpose. Here, it simply repeats the API’s name, but it could contain more details if needed.
endpoint: "/TransactionStatus"

The specific endpoint path for the API. This is appended to the base path to form the complete URL. For example, with basePath as /v1/cibbulkpayment, the full API path becomes /v1/cibbulkpayment/bulkPayment.
basePath: "/MerchantAPI/UPI2/v1"

The base path or root path for the API service. It often indicates the API version and organizational structure.
This is combined with the endpoint to form the complete URL for API requests.
method: "POST"

The HTTP method to use for this API request. POST indicates that this API requires a request body, which will likely contain necessary data (e.g., Upi payment status) to retrieve the relevant information.
headers: json { "Content-Type": "application/json" }

An object defining the HTTP headers required by the API. In this example:
Content-Type: Specifies that the request and response data format is application/json.
requestDtoType: "eazypay.model.request.TransactionStatusRequestDTO"


### Using the SDKClient.execute Method

The SDKClient.execute method is the main entry point for interacting with APIs in this SDK. It provides an overloaded method to support calling different APIs by specifying the API ID, module name, and request DTO type. This design allows flexibility for calling various API endpoints with a single method that returns a generic response.

#### Method Signature

python
response = function(dto( **payload))


The SDKClient.execute method is a flexible entry point for interacting with APIs in this SDK. It supports multiple modules and API calls by using a single method that is generic and adaptable to various DTOs and modules.

#### Method Signature Details

- **Type Parameter <T>**: Specifies the return type. The SDK uses generics to return the appropriate response DTO based on the API called.
- *Parameters*:
    - Json Payload: The Payload which is requiered for the api.
    - BaseDto dto: The super class for data transfer objects (DTOs) containing the request data.
- *Return Type*: A generic type which allows the method to return different types of response DTOs based on the specific API call.

### Example Usage

#### Example 1: Basic Call with API ID and Module

To call an API with just the API ID and module:

Python
// Calling the execute method with a function name  ,  request DTO and payload
response = function(dto( **payload))


This method will look up the configuration for the specified function  within the given module and send the request using the provided RequestDtoType.

#### Build Request:
Based on the specified dto (request DTO), it constructs the request payload.

#### Example
Here's an example of using annotation-based validation on a DTO class to enforce mandatory parameters:

python

from pydantic import BaseModel, Field


class QR3RequestDTO(BaseModel):
        terminalId: str
    amount: str
    billNumber: str
    validatePayerAccFlag: Optional[str] = None
    payerAccount: Optional[str] = None
    payerIFSC: Optional[str] = None
    signedIntentFlag: Optional[str] = None
    merchantId: str
    merchantTranId: str

    
    validityStartDateTime: Optional[str] = None
    validityEndDateTime: Optional[str] = None
    refid: Optional[str] =None
    update: Optional[str] = None

```
### Example: Calling a Specific API in the cibBulk Module

It is **mandatory** to load this configuration before invoking any SDK functions.

---

##  How to Load the `.env` File

To load environment variables from a `.env` file, use the utility provided in the SDK.

### Example:

```python
from httpcore.AppConstants import load_dotenv_from_path

# Specify the full path to the .env file
env_path = "D:/GitSdk/python-sdk-dev/default.env"

# Load the environment
load_dotenv_from_path(env_path)

---

## Runtime behaviour for SDK Client details 
It is mandatory to pass few System properties to make the SDK Integrated application to run. Means the application which has integrated with SDK client.

##For Api Testing

from eazypay.api import  QR3RequestDTO, transaction_status1 

from pydantic import BaseModel, Field

qr3Payload = {
    "amount" : "5.00",
    "billNumber" : "QR3",
    "validatePayerAccFlag" : "Y",
    "payerAccount" : "857679471234568955",
    "payerIFSC" : "AABC0876543",
    "merchantId" : "611429",
    "terminalId" : "5411",
    "merchantTranId" : "QR30987653456772188855",
    
    "update": "",
    "validityStartDateTime": "",
    "signedIntentFlag": "",
    "validityEndDateTime": "",

    "refId": ""

  }

 response = qr3(QR3RequestDTO( **qr3Payload))
 print("EAZYPAY Qr3 Status Response:\n" , response)

Here:
- "qr3" represents the the function for "QR3"
- "qr3Payload" is the request DTO containing the necessary request data.
- QRRequestDTO is the request DTO class to validate data.


## Configuration

Configuration for the env is given at the end of readme . 
create a .env or default.env file and add the confiquration in the file

## Configuring API KEYS

    Update the APIKEY for the module in the env file as required .


### Corporate module
```txt
EAZYPAY_API_KEY="secretapikey"
```


### Private key to decrypt the response recieved from the server are mandatory.
```
EAZYPAY_KEYSTORE_PATH="/home/username/certs/keystore.p12"
EAZYPAY_KEYSTORE_PASSWORD="secretpassword"
EAZYPAY_KEYSTORE_ALIAS="ICICI"  
```

Explanations

-KEYSTORE_PASSWORD: This parameter contains the password that protects the keystore. It is essential for accessing the keys and certificates stored within the keystore.

-KEYSTORE_PATH: This indicates where the keystore file is located on the file system. The application needs this path to load the keystore when needed.

-KEYSTORE_ALIAS: This alias refers to a specific private key within the keystore. It is used to identify and retrieve the private key for cryptographic operations such as signing or decryption.


Following system properties have to provide for the initiating requests from an SDK client.
### Accessing SDK Client Private Key

When initiating requests from an SDK client, the following system properties must be provided.

#### Keystore Details (PKCS#12)

- Keystore: A secure storage mechanism for cryptographic keys and certificates, often used to manage sensitive information in applications.
- Private Key: This key is essential for decryption and signing data. It is crucial that this key remains confidential to maintain the security of the application.
- Alias: A unique identifier for a specific key or certificate within the keystore. It is referenced during operations to ensure the correct key is used.

#### Keystore Properties

To configure the SDK client properly, the following properties must be defined:

- *EAZYPAY_KEYSTORE_PATH: The path to the keystore file. *(Note the Error message would be: Not provided)
- *EAZYPAY_KEYSTORE_PASSWORD: The password for accessing the keystore. *(Note the Error message would be: Not provided)
- *EAZYPAY_KEYSTORE_ALIAS: The alias for the private key stored in the keystore. *(Note the Error message would be: Not provided)

#### Private Key Errors

If there are issues related to the private key, the following errors may occur:

- No private key found in the keystore.
- Failed to load private key from the keystore.

#### Decryption Errors

Errors encountered during the decryption process may include:

- Failed to decrypt the encrypted key using RSA.
- Failed to decrypt the encrypted data using AES.
- Unexpected error during the decryption process.

#### Alias

- "Alias is not provided." This indicates that the alias for the private key has not been specified, which is necessary for successful decryption.


### Complete set of config required in the .env file. 
```txt

ENV_TYPE="UAT" 

LOG_LEVEL="INFO"
APPLICATION_JSON_CHARSET_UTF_8="application/json; charset=utf-8"
API_KEY="apiKey"
SHA_512="SHA-512"
X_ID_FINGERPRINT="X-ID-Fingerprint"
X_PRIORITY_HEADER="X-Priority"
ASYMMETRIC_CYPHER_RSA="RSA/ECB/PKCS1Padding"
SYMMETRIC_CYPHER_AES="AES/CBC/PKCS5Padding"
AES="AES"
CHAR_SET="abcdefghijklmnopqrstuvwxyz"
KEY_LENGTH="32"
IV_KEY_LENGTH="16"
WITH_RESPONSE_MODELS=false

COMPOSITE_API_KEY=
EAZYPAY_API_KEY=
CORPORATE_API_KEY=
CIBBULK_API_KEY=

EAZYPAY_KEYSTORE_PATH=
EAZYPAY_KEYSTORE_PASSWORD=
EAZYPAY_KEYSTORE_ALIAS=

```


### Base URL configuration in the sdk-config.json based on the environment


ENV_TYPE=PROD  (for production environment)

ENV_TYPE=UAT    (for uat testing environment)

### Convert PEM Files to P12 Format
To convert your private key (mykey.pem) and certificate (cert.pem) into a .p12 (PKCS#12) file, follow these steps:

## Requirements
OpenSSL must be installed on your system.

## You must have:

A private key file (mykey.pem)
A certificate file (cert.pem)

## Command
openssl pkcs12 -export -out mycert.p12 -inkey mykey.pem -in cert.pem

##  Callback Decryption Test Utility

### Overview

This script provides a test utility function `test_decryption()` to demonstrate how encrypted callback responses can be decrypted using the `decrypt_callback` method from the `httpcore.utils.CallbackUtils` module. It simulates a callback response received from services and   decrypt the payload using preconfigured cryptographic parameters.

---

### Source: `test_decryption.py`

```python
from httpcore.utils.CallbackUtils import decrypt_callback

def test_decryption():
    encrypted_data = {
        'requestId': '',
        'service': 'UPI',
        'encryptedKey': 'll9UqF/fWH/... ',
        'oaepHashingAlgorithm': 'NONE',
        'iv': '',
        'encryptedData': '+v7vE3Tx/qCEop2GE0...',
        'clientInfo': '',
        'optionalParam': ''
    }

    decrypted = decrypt_callback(encrypted_data)
    print("Decrypted response:", decrypted)


if __name__ == "__main__":
    test_decryption()

