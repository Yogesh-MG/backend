from .model import *
from httpcore.http.CoreHttpClient import CoreHttpClient
from httpcore.AppConstants import AppConstants

with_dto = AppConstants.WITH_RESPONSE_MODELS

client = CoreHttpClient()

def api_call(endpoint, method, body, kwargs):
    headers = { 
                "Content-Type": "application/json",
                "X-SDK-Originated": "true",
            }
    
    return client.common_api_call(endpoint, body, kwargs)

              
def transaction_status(body: TransactionStatusRequestDTO)-> TransactionStatusResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3001
        Name: TransactionStatus
        Path: /MerchantAPI/UPI2/v1/TransactionStatus
        Category: 

    Args: TransactionStatusRequestDTO
    Returns: TransactionStatusResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/TransactionStatus"
    if AppConstants.SV_ENABLED:
        endpoint = "/MerchantAPI/UPI2_sv/v1/TransactionStatus"  
    else:
        endpoint = "/MerchantAPI/UPI2/v1/TransactionStatus" 
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else TransactionStatusResponseDTO(**res_body)

            
def create_mandate(body: CreateMandateRequestDTO)-> CreateMandateResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3002
        Name: CreateMandate
        Path: /MerchantAPI/UPI2/v1/CreateMandate
        Category: 

    Args: CreateMandateRequestDTO
    Returns: CreateMandateResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/CreateMandate"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CreateMandateResponseDTO(**res_body)

            
def mandate_notification(body: MandateNotificationRequestDTO)-> MandateNotificationResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3003
        Name: MandateNotification
        Path: /MerchantAPI/UPI2/v1/MandateNotification
        Category: 

    Args: MandateNotificationRequestDTO
    Returns: MandateNotificationResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/MandateNotification"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else MandateNotificationResponseDTO(**res_body)

            
def transaction_status_bycriteria(body: TransactionstatusbycriteriaRequestDTO)-> TransactionStatusbyCriteriaResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3004
        Name: Transaction Status By criteria
        Path: /MerchantAPI/UPI2/v1/TransactionStatusByCriteria
        Category: 

    Args: TransactionstatusbycriteriaRequestDTO
    Returns: TransactionStatusbyCriteriaResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/TransactionStatusByCriteria"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else TransactionStatusbyCriteriaResponseDTO(**res_body)

            
def refund(body: RefundRequestDTO)-> RefundStatusResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3005
        Name: Refund
        Path: /MerchantAPI/UPI2/v1/Refund
        Category: 

    Args: RefundRequestDTO
    Returns: RefundStatusResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/Refund"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else RefundStatusResponseDTO(**res_body)

            
def qr(body: QRRequestDTO)-> QRResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3006
        Name: QR
        Path: /MerchantAPI/UPI2/v1/QR
        Category: 

    Args: QRRequestDTO
    Returns: QRResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/QR"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else QRResponseDTO(**res_body)

            
def collect_pay(body: CollectPayRequestDTO)-> CollectPayResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3007
        Name: Collect Pay
        Path: /MerchantAPI/UPI2/v1/CollectPay
        Category: 

    Args: CollectPayRequestDTO
    Returns: CollectPayResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/CollectPay"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CollectPayResponseDTO(**res_body)

            
def validate_voucher(body: ValidateVoucherRequestDTO)-> ValidateVoucherResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3008
        Name: ValidateVoucher
        Path: /MerchantAPI/UPI2/v1/ValidateVoucher
        Category: 

    Args: ValidateVoucherRequestDTO
    Returns: ValidateVoucherResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/ValidateVoucher"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else ValidateVoucherResponseDTO(**res_body)

            
def redeem_voucher(body: RedeemVoucherRequestDTO)-> RedeemVoucherResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3009
        Name: RedeemVoucher
        Path: /MerchantAPI/UPI2/v1/RedeemVoucher
        Category: 

    Args: RedeemVoucherRequestDTO
    Returns: RedeemVoucherResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/RedeemVoucher"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else RedeemVoucherResponseDTO(**res_body)

            
def execute_mandate(body: ExecuteMandateRequestDTO)-> ExecuteMandateResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3010
        Name: ExecuteMandate
        Path: /MerchantAPI/UPI2/v1/ExecuteMandate
        Category: 

    Args: ExecuteMandateRequestDTO
    Returns: ExecuteMandateResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/ExecuteMandate"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else ExecuteMandateResponseDTO(**res_body)

            
def create_vouchers(body: CreateVouchersRequestDTO)-> CreateVoucherResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3011
        Name: CreateVouchers
        Path: /MerchantAPI/UPI2/v1/CreateVouchers
        Category: 

    Args: CreateVouchersRequestDTO
    Returns: CreateVoucherResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/CreateVouchers"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CreateVoucherResponseDTO(**res_body)

            
def delayed_settlements(body: DelayedSettlementsRequestDTO)-> DelayedSettlementResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3012
        Name: DelayedSettlements
        Path: /MerchantAPI/UPI2/v1/DelayedSettlements
        Category: 

    Args: DelayedSettlementsRequestDTO
    Returns: DelayedSettlementResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/DelayedSettlements"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else DelayedSettlementResponseDTO(**res_body)

            
def qr1(body: QR1RequestDTO)-> QR123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3013
        Name: QR1
        Path: /MerchantAPI/UPI/v0/QR
        Category: 

    Args: QR1RequestDTO
    Returns: QR123ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/QR/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else QR123ResponseDTO(**res_body)

            
def qr2(body: QR2RequestDTO)-> QR123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3014
        Name: QR2
        Path: /MerchantAPI/UPI/v0/QR2
        Category: 

    Args: QR2RequestDTO
    Returns: QR123ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/QR2/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else QR123ResponseDTO(**res_body)

            
def qr3(body: QR3RequestDTO)-> QR123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3015
        Name: QR3
        Path: /MerchantAPI/UPI/v0/QR3
        Category: 

    Args: QR3RequestDTO
    Returns: QR123ResponseDTO
    '''
    if AppConstants.SV_ENABLED:
        endpoint = f"/EAZYPAY-SV/QR3/{body.merchantId}"  # Example SV-specific endpoint
    else:
        endpoint = f"/MerchantAPI/UPI/v0/QR3/{body.merchantId}"    
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else QR123ResponseDTO(**res_body)

            
def collect_pay1(body: CollectPay1RequestDTO)-> CollectPay123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3016
        Name: CollectPay1
        Path: /MerchantAPI/UPI/v0/CollectPay1
        Category: 

    Args: CollectPay1RequestDTO
    Returns: CollectPay123ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/CollectPay1/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CollectPay123ResponseDTO(**res_body)

            
def collect_pay2(body: CollectPay2RequestDTO)-> CollectPay123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3017
        Name: CollectPay2
        Path: /MerchantAPI/UPI/v0/CollectPay2
        Category: 

    Args: CollectPay2RequestDTO
    Returns: CollectPay123ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/CollectPay2/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CollectPay123ResponseDTO(**res_body)

            
def collect_pay3(body: CollectPay3RequestDTO)-> CollectPay123ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3018
        Name: CollectPay3
        Path: /MerchantAPI/UPI/v0/CollectPay3
        Category: 

    Args: CollectPay3RequestDTO
    Returns: CollectPay123ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/CollectPay3/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CollectPay123ResponseDTO(**res_body)

            
def transaction_status1(body: TransactionStatus1RequestDTO)-> TransactionStatus12ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3019
        Name: TransactionStatus1
        Path: /MerchantAPI/UPI/v0/TransactionStatus1
        Category: 

    Args: TransactionStatus1RequestDTO
    Returns: TransactionStatus12ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/TransactionStatus1/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else TransactionStatus12ResponseDTO(**res_body)

            
def transaction_status2(body: TransactionStatus2RequestDTO)-> TransactionStatus12ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3020
        Name: TransactionStatus2
        Path: /MerchantAPI/UPI/v0/TransactionStatus2
        Category: 

    Args: TransactionStatus2RequestDTO
    Returns: TransactionStatus12ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/TransactionStatus2/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else TransactionStatus12ResponseDTO(**res_body)

            
def transaction_status3(body: TransactionStatus3RequestDTO)-> TransactionStatus3ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3021
        Name: TransactionStatus3
        Path: /MerchantAPI/UPI/v0/TransactionStatus3
        Category: 

    Args: TransactionStatus3RequestDTO
    Returns: TransactionStatus3ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/TransactionStatus3/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else TransactionStatus3ResponseDTO(**res_body)

            
def refund1(body: Refund1RequestDTO)-> RefundAPI12ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3022
        Name: Refund1
        Path: /MerchantAPI/UPI/v0/Refund
        Category: 

    Args: Refund1RequestDTO
    Returns: RefundAPI12ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/Refund/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else RefundAPI12ResponseDTO(**res_body)

            
def refund2(body: Refund2RequestDTO)-> RefundAPI12ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3023
        Name: Refund2
        Path: /MerchantAPI/UPI/v0/Refund2
        Category: 

    Args: Refund2RequestDTO
    Returns: RefundAPI12ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/Refund2/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else RefundAPI12ResponseDTO(**res_body)

            
def callback_status1(body: CallbackStatus1RequestDTO)-> CallbackStatus1ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3024
        Name: CallbackStatus1
        Path: /MerchantAPI/UPI/v0/CallbackStatus
        Category: 

    Args: CallbackStatus1RequestDTO
    Returns: CallbackStatus1ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/CallbackStatus/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CallbackStatus1ResponseDTO(**res_body)

def callback_status2(body: CallbackStatus2RequestDTO)-> CallbackStatus2ResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 3025
        Name: CallbackStatus2
        Path: /MerchantAPI/UPI/v0/CallbackStatus2
        Category: 

    Args: CallbackStatus2RequestDTO
    Returns: CallbackStatus2ResponseDTO
    '''
    endpoint = f"/MerchantAPI/UPI/v0/CallbackStatus2/{body.merchantId}"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else CallbackStatus2ResponseDTO(**res_body)

            
def update_mandate(body: UpdateMandateRequestDTO)-> UpdateMandateResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 
        Name: UpdateMandate
        Path: /MerchantAPI/UPI2/v1/CreateMandate
        Category: 

    Args: UpdateMandateRequestDTO
    Returns: UpdateMandateResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/CreateMandate"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else UpdateMandateResponseDTO(**res_body)


def revoke_mandate(body: RevokeMandateRequestDTO)-> RevokeMandateResponseDTO:
    '''
    API Details: 
        Module: eazypay
        Id: 
        Name: RevokeMandate
        Path: /MerchantAPI/UPI2/v1/CreateMandate
        Category: 

    Args: RevokeMandateRequestDTO
    Returns: RevokeMandateResponseDTO
    '''
    endpoint = "/MerchantAPI/UPI2/v1/CreateMandate"
    method = "POST"
    kwargs = { 'name': 'eazypay'}
    res_body = api_call(endpoint, method, body, kwargs)
    return res_body if with_dto is False else RevokeMandateResponseDTO(**res_body)
